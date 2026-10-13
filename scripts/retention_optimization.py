"""Retrospective decision prototype; intervention economics are simulated."""
from pathlib import Path
import sys
import json
import time
from itertools import product

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / '.optimization-deps').exists():
    sys.path.insert(0, str(ROOT / '.optimization-deps'))

import duckdb
import joblib
import numpy as np
import pandas as pd
import pyomo.environ as pyo
import gurobipy
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

REPORTS = ROOT / 'reports' / 'optimization'
LOCAL = ROOT / 'data' / 'processed' / 'retention_optimization'
COSTS = np.array([0.2, 2.0])
CAPACITY = np.array([150, 60])
BUDGETS = [30, 60, 120, 200]
SCENARIOS = ['weak', 'base', 'strong']
MULTIPLIERS = np.array([[0.4, 0.3], [1.0, 1.0], [1.4, 1.5]])


def prepare_inputs():
    """Refit the existing fixed LR specification on historical users only."""
    features = json.loads((ROOT / 'reports/combined_feature_config.json').read_text())['features']
    source = ROOT / 'data/processed'
    con = duckdb.connect()
    train = con.read_parquet(str(source / 'historical_combined_features_20161130.parquet')).df()
    model = Pipeline([
        ('imputer', SimpleImputer(strategy='median', add_indicator=True)),
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(train[features].astype('float64'), train['is_churn'].astype('int8'))
    train_count = len(train)
    del train
    later_path = str(source / 'later_combined_features_20170228.parquet')
    later = con.read_parquet(later_path).df()
    probabilities = model.predict_proba(later[features].astype('float64'))[:, 1]
    quality = {
        'historical_training_users': train_count,
        'later_evaluation_users': len(later),
        'later_log_loss': log_loss(later['is_churn'], probabilities),
        'later_roc_auc': roc_auc_score(later['is_churn'], probabilities),
        'independent_test': False,
    }
    later['churn_probability'] = probabilities
    # Deterministic identifier-hash sample, independent of labels and outcomes.
    con.register('later', later)
    sample = con.sql('SELECT * EXCLUDE (is_churn) FROM later ORDER BY md5(msno), msno LIMIT 750').df()
    rng = np.random.default_rng(42)
    # Neither customer margin nor intervention response is observed in KKBOX.
    sample['assumed_retained_margin'] = np.clip(rng.lognormal(np.log(100), 0.4, len(sample)), 30, 250)
    activity = sample['recorded_days_recent_7d'].to_numpy() / 7
    renewal = sample['auto_renew_share_90d'].fillna(0.5).to_numpy()
    jitter = rng.uniform(0.8, 1.2, (len(sample), 2))
    relative_reduction = np.column_stack([0.04 + 0.10 * activity, 0.10 + 0.20 * (1 - renewal)]) * jitter
    delta = sample['churn_probability'].to_numpy()[:, None] * relative_reduction
    uplifts = np.minimum(delta[:, :, None] * MULTIPLIERS.T[None, :, :],
                        sample['churn_probability'].to_numpy()[:, None, None])
    profits = uplifts * sample['assumed_retained_margin'].to_numpy()[:, None, None] - COSTS[None, :, None]
    assert np.isfinite(profits).all() and (uplifts >= 0).all()
    for a, name in enumerate(['reminder', 'discount']):
        sample[f'assumed_{name}_base_uplift'] = uplifts[:, a, 1]
    LOCAL.mkdir(parents=True, exist_ok=True)
    con.from_df(sample).write_parquet(str(LOCAL / 'inputs.parquet'))
    joblib.dump(model, ROOT / 'models/retention_logistic_regression.joblib')
    con.close()
    return sample, profits, uplifts, quality


def validate_assignment(x, budget, capacity):
    assert np.isin(x, [0, 1]).all()
    assert (x.sum(axis=1) <= 1).all()
    assert (x.sum(axis=0) <= capacity).all()
    assert float((x * COSTS).sum()) <= budget + 1e-6


def optimize(profits, budget, capacity, robust=False):
    """Binary multiple-choice allocation; optional maximin scenario objective."""
    n = len(profits)
    m = pyo.ConcreteModel()
    m.users = pyo.RangeSet(0, n - 1)
    m.actions = pyo.RangeSet(0, 1)
    m.x = pyo.Var(m.users, m.actions, domain=pyo.Binary)
    m.one_action = pyo.Constraint(m.users, rule=lambda m, i: sum(m.x[i, a] for a in m.actions) <= 1)
    m.budget = pyo.Constraint(expr=sum(COSTS[a] * m.x[i, a] for i in m.users for a in m.actions) <= budget)
    m.capacity = pyo.Constraint(m.actions, rule=lambda m, a: sum(m.x[i, a] for i in m.users) <= int(capacity[a]))
    if robust:
        m.floor = pyo.Var(domain=pyo.Reals)
        m.scenarios = pyo.RangeSet(0, profits.shape[2] - 1)
        m.scenario_floor = pyo.Constraint(m.scenarios, rule=lambda m, s:
            m.floor <= sum(profits[i, a, s] * m.x[i, a] for i in m.users for a in m.actions))
        m.objective = pyo.Objective(expr=m.floor, sense=pyo.maximize)
    else:
        m.objective = pyo.Objective(expr=sum(profits[i, a, 1] * m.x[i, a] for i in m.users for a in m.actions), sense=pyo.maximize)
    start = time.perf_counter()
    with pyo.SolverFactory('gurobi_direct', manage_env=True) as solver:
        result = solver.solve(m, options={'Threads': 2, 'Seed': 42, 'MIPGap': 0.0, 'TimeLimit': 60}, tee=False)
    seconds = time.perf_counter() - start
    assert result.solver.termination_condition == pyo.TerminationCondition.optimal, str(result.solver)
    x = np.array([[round(pyo.value(m.x[i, a])) for a in m.actions] for i in m.users], dtype=int)
    validate_assignment(x, budget, capacity)
    lower, upper = float(result.problem.lower_bound), float(result.problem.upper_bound)
    meta = {'termination': str(result.solver.termination_condition), 'solve_seconds': seconds,
            'objective': pyo.value(m.objective), 'lower_bound': lower, 'upper_bound': upper,
            'absolute_gap': abs(upper - lower), 'binary_variables': n * 2,
            'constraints': n + 3 + (profits.shape[2] if robust else 0)}
    return x, meta


def greedy(profits, risk, budget, capacity, kind, seed=0):
    """All heuristics share the same costs, constraints, and candidate actions."""
    base = profits[:, :, 1]
    if kind == 'value_per_cost':
        # Recompute marginal value/cost after each choice, allowing reminder
        # recipients to upgrade to discounts rather than locking early choices.
        x = np.zeros(base.shape, dtype=int)
        counts = np.zeros(2, dtype=int)
        spent = 0.0
        while True:
            candidates = []
            for i in range(len(risk)):
                old = int(np.argmax(x[i])) if x[i].sum() else -1
                for a in range(2):
                    if a == old:
                        continue
                    dc = COSTS[a] - (COSTS[old] if old >= 0 else 0)
                    dv = base[i, a] - (base[i, old] if old >= 0 else 0)
                    if dc <= 0 or dv <= 0 or counts[a] >= capacity[a] or spent + dc > budget + 1e-9:
                        continue
                    candidates.append((dv / dc, -i, -a, i, a, old, dc))
            if not candidates:
                break
            _, _, _, i, a, old, dc = max(candidates)
            if old >= 0:
                x[i, old] = 0
                counts[old] -= 1
            x[i, a] = 1
            counts[a] += 1
            spent += dc
        validate_assignment(x, budget, capacity)
        return x
    pairs = [(i, a) for i in range(len(risk)) for a in range(2) if base[i, a] > 0]
    if kind == 'risk_priority':
        pairs.sort(key=lambda ia: (-risk[ia[0]], -base[ia], ia))
    elif kind == 'random':
        np.random.default_rng(seed).shuffle(pairs)
    else:
        raise ValueError(kind)
    x = np.zeros(base.shape, dtype=int)
    counts = np.zeros(2, dtype=int)
    spent = 0.0
    for i, a in pairs:
        if x[i].sum() or counts[a] >= capacity[a] or spent + COSTS[a] > budget + 1e-9:
            continue
        x[i, a] = 1
        counts[a] += 1
        spent += COSTS[a]
    validate_assignment(x, budget, capacity)
    return x


def score(x, profits, uplifts, budget, strategy, run=0):
    scenario_values = (x[:, :, None] * profits).sum(axis=(0, 1))
    row = {'budget': budget, 'strategy': strategy, 'run': run,
           'spend': float((x * COSTS).sum()), 'reminders': int(x[:, 0].sum()),
           'discounts': int(x[:, 1].sum()), 'contacted': int(x.sum()),
           'base_expected_incremental_retained': float((x * uplifts[:, :, 1]).sum()),
           'worst_scenario_net_value': float(scenario_values.min())}
    row.update({f'{s}_net_value': float(scenario_values[j]) for j, s in enumerate(SCENARIOS)})
    return row


def verify_small_model():
    # Independent enumeration oracle for both nominal and robust formulations.
    base = np.array([[0.8, 1.0], [3.8, 6.0], [1.8, 1.0]])
    profits = np.stack([base - np.array([0.4, 2.0]), base, base + 1], axis=2)
    checked = []
    for robust in [False, True]:
        values = []
        for choices in product([-1, 0, 1], repeat=3):
            x = np.zeros((3, 2), dtype=int)
            for i, a in enumerate(choices):
                if a >= 0:
                    x[i, a] = 1
            if (x * COSTS).sum() <= 2.4 + 1e-9:
                scenarios = (x[:, :, None] * profits).sum(axis=(0, 1))
                values.append(scenarios.min() if robust else scenarios[1])
        x, meta = optimize(profits, 2.4, np.array([3, 3]), robust)
        assert abs(meta['objective'] - max(values)) < 1e-6
        checked.append({'robust': robust, 'enumeration_optimum': max(values), 'solver_optimum': meta['objective']})
    return checked


def run():
    REPORTS.mkdir(parents=True, exist_ok=True)
    checks = verify_small_model()
    print('Enumeration checks passed.', flush=True)
    users, profits, uplifts, quality = prepare_inputs()
    print('Historical LR refit and 750-user inputs prepared:', quality, flush=True)
    risk = users['churn_probability'].to_numpy()
    rows, solver_rows = [], []
    for budget in BUDGETS:
        nominal, nm = optimize(profits, budget, CAPACITY)
        robust, rm = optimize(profits, budget, CAPACITY, robust=True)
        for name, x, meta in [('nominal_milp', nominal, nm), ('robust_maximin', robust, rm)]:
            rows.append(score(x, profits, uplifts, budget, name))
            solver_rows.append({'budget': budget, 'strategy': name, **meta})
            if budget == 120:
                assignments = users[['msno', 'churn_probability', 'assumed_retained_margin']].copy()
                assignments['action'] = np.where(x[:, 1], 'discount', np.where(x[:, 0], 'reminder', 'none'))
                with duckdb.connect() as output_con:
                    output_con.from_df(assignments).write_parquet(str(LOCAL / f'{name}_assignments.parquet'))
        for kind in ['risk_priority', 'value_per_cost']:
            x = greedy(profits, risk, budget, CAPACITY, kind)
            assert (x * profits[:, :, 1]).sum() <= nm['objective'] + 1e-5
            rows.append(score(x, profits, uplifts, budget, kind))
        for seed in range(100):
            x = greedy(profits, risk, budget, CAPACITY, 'random', seed)
            assert (x * profits[:, :, 1]).sum() <= nm['objective'] + 1e-5
            rows.append(score(x, profits, uplifts, budget, 'random', seed))
        assert (robust[:, :, None] * profits).sum(axis=(0, 1)).min() >= (nominal[:, :, None] * profits).sum(axis=(0, 1)).min() - 1e-5
        print(f'Budget {budget}: nominal objective {nm["objective"]:.2f}, robust worst-case {rm["objective"]:.2f}', flush=True)
    results = pd.DataFrame(rows)
    results.to_csv(REPORTS / 'strategy_results.csv', index=False)
    aggregate = results.groupby(['budget', 'strategy']).agg(
        runs=('run', 'count'), spend=('spend', 'mean'), contacted=('contacted', 'mean'),
        reminders=('reminders', 'mean'), discounts=('discounts', 'mean'),
        base_net_value=('base_net_value', 'mean'), weak_net_value=('weak_net_value', 'mean'),
        strong_net_value=('strong_net_value', 'mean'), worst_scenario_net_value=('worst_scenario_net_value', 'mean'),
        base_expected_incremental_retained=('base_expected_incremental_retained', 'mean'),
        base_net_value_std=('base_net_value', 'std')).reset_index()
    aggregate.to_csv(REPORTS / 'strategy_summary.csv', index=False)
    for strategy in ['nominal_milp', 'robust_maximin']:
        objective = 'base_net_value' if strategy == 'nominal_milp' else 'worst_scenario_net_value'
        assert np.all(np.diff(aggregate.loc[aggregate.strategy == strategy].sort_values('budget')[objective]) >= -1e-5)
    pd.DataFrame(solver_rows).to_csv(REPORTS / 'solver_results.csv', index=False)
    config = {'status': 'retrospective prototype with simulated economics; no intervention delivered',
        'sample_users': len(users), 'sample_rule': 'first 750 user IDs ordered by md5(msno), msno; no labels used',
        'candidate_eligibility': 'assumed; no consent or active subscription verification',
        'value_units': 'hypothetical monetary units, not actual currency or observed revenue',
        'seed': 42, 'budgets': BUDGETS, 'costs': dict(zip(['reminder', 'discount'], COSTS.tolist())),
        'capacities': CAPACITY.tolist(), 'assumed_margin': 'Lognormal(log(100), 0.4), clipped to [30,250]',
        'assumed_relative_risk_reductions': {'reminder': '(0.04 + 0.10 * recent_recorded_days / 7) * Uniform(0.8,1.2)',
            'discount': '(0.10 + 0.20 * (1 - auto_renew_share)) * Uniform(0.8,1.2); missing share=0.5'},
        'uplift_formula': 'predicted churn probability * assumed relative risk reduction * scenario multiplier, capped at baseline risk',
        'scenario_multipliers': dict(zip(SCENARIOS, MULTIPLIERS.tolist())),
        'scenario_probabilities': 'not specified; maximin robustness, not stochastic or multistage programming',
        'random_baseline': '100 seeded random permutations of positive-base-value user/action pairs',
        'prediction_quality': quality, 'enumeration_checks': checks,
        'versions': {'pyomo': __import__('pyomo').__version__, 'gurobi': list(gurobipy.gurobi.version())}}
    (REPORTS / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    plot(aggregate)
    print(aggregate.loc[aggregate.budget == 120].to_string(index=False), flush=True)
    return aggregate


def plot(summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    labels = {'nominal_milp': 'Nominal MILP', 'robust_maximin': 'Robust maximin',
              'risk_priority': 'Risk priority', 'value_per_cost': 'Value/cost greedy', 'random': 'Random (100 runs mean)'}
    for name, label in labels.items():
        d = summary.loc[summary.strategy == name].sort_values('budget')
        axes[0].plot(d.budget, d.base_net_value, marker='o', label=label)
        axes[1].plot(d.budget, d.worst_scenario_net_value, marker='o', label=label)
    for ax, title in zip(axes, ['Base-assumption net value', 'Worst-scenario net value']):
        ax.set(title=title, xlabel='Budget (hypothetical units)', ylabel='Simulated expected net value')
        ax.grid(alpha=0.25)
    axes[0].legend(fontsize=8)
    fig.suptitle('KKBOX retention allocation | 750 users | simulated intervention economics', fontsize=11)
    fig.tight_layout()
    fig.savefig(REPORTS / 'budget_sensitivity.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    run()
