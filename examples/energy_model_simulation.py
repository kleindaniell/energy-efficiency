from sd_simulation import Simulation, SimVariable, VariableType, InfluenceMode
from typing import Dict, List
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_model() -> Dict[str, SimVariable]:
    """Create an system dynamics model."""
    
    variables = {
        "Fomento PFP": SimVariable("Fomento PFP", 0.1, VariableType.STOCK),
        "Políticas EE": SimVariable("Políticas EE", 0.1, VariableType.AUXILIARY),
        "Adoção AEE": SimVariable("Adoção AEE", 0.1, VariableType.STOCK, accept_negative=False),
        "Consumo de Energia": SimVariable("Consumo de Energia", 1.0, VariableType.STOCK, accept_negative=False),
        "Custos Operacionais": SimVariable("Custos Operacionais", 0.5, VariableType.STOCK, accept_negative=False),
        "Investimento no Negócio": SimVariable("Investimento no Negócio", 0.2, VariableType.STOCK, accept_negative=False),
        "Geração de Emprego": SimVariable("Geração de Emprego", 0.3, VariableType.STOCK, accept_negative=False),
        "Atividade Econômica": SimVariable("Atividade Econômica", 0.3, VariableType.STOCK, accept_negative=False),
        "Resultado Operacional": SimVariable("Resultado Operacional", 0.1, VariableType.STOCK),
        "Faturamento": SimVariable("Faturamento", 0.3, VariableType.STOCK, accept_negative=False),
        "Receita Tributária": SimVariable("Receita Tributária", 0.2, VariableType.STOCK, accept_negative=False),
        "Taxa Adoção": SimVariable("Taxa Adoção", 0.05, VariableType.FLOW, accept_negative=False),
        "Taxa Investimento": SimVariable("Taxa Investimento", 0.1, VariableType.FLOW, accept_negative=False),
    }
    
    variables["Políticas EE"].add_influence(variables["Fomento PFP"], weight=0.1, mode=InfluenceMode.LOGISTIC)
    variables["Taxa Adoção"].add_influence(variables["Políticas EE"], weight=0.1, delay=2)
    variables["Adoção AEE"].add_inflow(variables["Taxa Adoção"])
    
    variables["Consumo de Energia"].add_influence(variables["Adoção AEE"], weight=-0.1, mode=InfluenceMode.SATURATION)
    variables["Custos Operacionais"].add_influence(variables["Consumo de Energia"], weight=0.08)
    
    variables["Taxa Investimento"].add_influence(variables["Custos Operacionais"], weight=-0.05)
    variables["Taxa Investimento"].add_influence(variables["Resultado Operacional"], weight=0.15)
    variables["Investimento no Negócio"].add_inflow(variables["Taxa Investimento"])
    
    variables["Geração de Emprego"].add_influence(variables["Investimento no Negócio"], weight=0.1, mode=InfluenceMode.THRESHOLD, threshold=0.1)
    variables["Atividade Econômica"].add_influence(variables["Investimento no Negócio"], weight=0.12)
    variables["Atividade Econômica"].add_influence(variables["Geração de Emprego"], weight=0.08)
    
    variables["Resultado Operacional"].add_influence(variables["Faturamento"], weight=0.1)
    variables["Resultado Operacional"].add_influence(variables["Custos Operacionais"], weight=-0.15)
    
    variables["Faturamento"].add_influence(variables["Atividade Econômica"], weight=0.12)
    variables["Faturamento"].add_influence(variables["Adoção AEE"], weight=0.08, delay=1)
    
    variables["Receita Tributária"].add_influence(variables["Geração de Emprego"], weight=0.1)
    variables["Receita Tributária"].add_influence(variables["Faturamento"], weight=0.12)
    
    variables["Fomento PFP"].add_influence(variables["Receita Tributária"], weight=0.1, delay=3)
    variables["Políticas EE"].add_influence(variables["Atividade Econômica"], weight=0.05, delay=2)
    
    return variables

def create_plots(results: Dict[str, List[float]], time_series: List[float], 
                         sim: Simulation) -> go.Figure:
    """Create system dynamics plots."""
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Main Variables', 'Economic Indicators', 'Policy Variables', 'Phase Space'),
        specs=[[{"secondary_y": True}, {"secondary_y": True}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    main_vars = ["Adoção AEE", "Consumo de Energia", "Investimento no Negócio"]
    for var_name in main_vars:
        if var_name in results:
            fig.add_trace(
                go.Scatter(x=time_series, y=results[var_name], name=var_name, line=dict(width=3)),
                row=1, col=1
            )
    
    econ_vars = ["Faturamento", "Geração de Emprego", "Atividade Econômica"]
    for var_name in econ_vars:
        if var_name in results:
            fig.add_trace(
                go.Scatter(x=time_series, y=results[var_name], name=var_name, line=dict(width=2)),
                row=1, col=2
            )
    
    policy_vars = ["Fomento PFP", "Políticas EE", "Receita Tributária"]
    for var_name in policy_vars:
        if var_name in results:
            fig.add_trace(
                go.Scatter(x=time_series, y=results[var_name], name=var_name, line=dict(width=2)),
                row=2, col=1
            )
    
    if "Investimento no Negócio" in results and "Atividade Econômica" in results:
        fig.add_trace(
            go.Scatter(
                x=results["Investimento no Negócio"], 
                y=results["Atividade Econômica"],
                mode='lines+markers',
                name='Phase Space',
                line=dict(width=2),
                marker=dict(size=4)
            ),
            row=2, col=2
        )
    
    fig.update_layout(
        title='System Dynamics Analysis',
        height=800,
        showlegend=True,
        template='plotly_white'
    )
    
    return fig

if __name__ == "__main__":
    TIME_STEPS = 36
    DT = 1

    variables = create_model()
    sim = Simulation(variables, time_steps=TIME_STEPS, dt=DT, integration_method="rk4")

    print("Running system dynamics simulation...")
    sim.run()

    results = sim.get_results()
    time_series = sim.get_time_series()

    fig = create_plots(results, time_series, sim)
    fig.show()

    print("\n=== System Analysis ===")
    print(f"Simulation completed in {sim.current_step + 1} steps")

    print("\nFinal Values:")
    for name, var in variables.items():
        if var.var_type != VariableType.CONSTANT:
            rate = var.get_rate_of_change()
            print(f"{name}: {var.value:.3f} (rate: {rate:.4f})")

    print("\n=== Sensitivity Analysis ===")
    print("Analyzing sensitivity to 'Fomento PFP' initial value...")
    sensitivity_results = sim.sensitivity_analysis("Fomento PFP", (0.5, 0.9), steps=20)

    for param_value, scenario_results in sensitivity_results.items():
        final_activity = scenario_results["Atividade Econômica"][-1]
        print(f"Fomento PFP = {param_value:.3f} → Final Economic Activity = {final_activity:.3f}")
