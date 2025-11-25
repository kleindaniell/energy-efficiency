import math
from typing import Any
from ..engine import SimVariable, VariableType, Simulation

class FapergsRGEModel:
    def __init__(self):
        # --- Parameters (Constants from "Parametros" sheet) ---
        self.TARIFA_R_MWh = SimVariable("TARIFA_R_MWh", 650, VariableType.CONSTANT)
        self.ICMS_TAU = SimVariable("ICMS_TAU", 0.25, VariableType.CONSTANT)
        self.theta1 = SimVariable("theta1", 0.0008, VariableType.CONSTANT)
        self.eta = SimVariable("eta", 0.3, VariableType.CONSTANT)
        self.rebote_frac = SimVariable("rebote_frac", 0.1, VariableType.CONSTANT)
        self.k_eff_inv = SimVariable("k_eff_inv", 0.0008, VariableType.CONSTANT)
        self.k_eff_sge = SimVariable("k_eff_sge", 0.03, VariableType.CONSTANT)
        self.k_eff_cap = SimVariable("k_eff_cap", 0.01, VariableType.CONSTANT)
        self.k_eff_bar = SimVariable("k_eff_bar", 0.02, VariableType.CONSTANT)
        self.k_gd_inv = SimVariable("k_gd_inv", 0.001, VariableType.CONSTANT)
        self.k_gd_pol = SimVariable("k_gd_pol", 0.015, VariableType.CONSTANT)
        self.theta_en_cost = SimVariable("theta_en_cost", 1, VariableType.CONSTANT)
        self.theta_ineff = SimVariable("theta_ineff", 60000, VariableType.CONSTANT)
        self.theta_prod_comp = SimVariable("theta_prod_comp", 600000, VariableType.CONSTANT)
        self.theta_prod_cost = SimVariable("theta_prod_cost", 0.08, VariableType.CONSTANT)
        self.k_info_cap = SimVariable("k_info_cap", 0.4, VariableType.CONSTANT)
        self.k_info_pol = SimVariable("k_info_pol", 0.25, VariableType.CONSTANT)
        self.k_info_bar = SimVariable("k_info_bar", 0.15, VariableType.CONSTANT)
        self.k_bar_pol = SimVariable("k_bar_pol", 0.45, VariableType.CONSTANT)
        self.k_bar_info = SimVariable("k_bar_info", 0.35, VariableType.CONSTANT)
        self.k_bar_cred = SimVariable("k_bar_cred", 0.35, VariableType.CONSTANT)
        self.k_cred_green = SimVariable("k_cred_green", 0.55, VariableType.CONSTANT)
        self.k_cred_pol = SimVariable("k_cred_pol", 0.25, VariableType.CONSTANT)
        self.beta_ICMS_EE = SimVariable("beta_ICMS_EE", 0.12, VariableType.CONSTANT)
        self.delta_ICMS_insumos = SimVariable("delta_ICMS_insumos", 0.018, VariableType.CONSTANT)
        self.k_comp_eff = SimVariable("k_comp_eff", 3, VariableType.CONSTANT)
        self.k_comp_cost = SimVariable("k_comp_cost", 5e-8, VariableType.CONSTANT)
        self.POLITICAS = SimVariable("POLITICAS", 0.55, VariableType.CONSTANT)
        self.FIN_GREEN = SimVariable("FIN_GREEN", 0.65, VariableType.CONSTANT)

        # --- Variables (from "Variaveis" sheet) ---
        
        # V01: Consumo (MWh/mês) - Auxiliar
        self.v01 = SimVariable("V01", 0, VariableType.AUXILIARY, equation_func=self._v01_equation)
        # V02: Tarifa (R$/MWh) - Constant (already covered by TARIFA_R_MWh parameter)
        self.v02 = SimVariable("V02", 650, VariableType.CONSTANT) # Explicitly define as constant for clarity
        # V03: Eficiência (0–1) - Estoque
        self.v03 = SimVariable("V03", 0.25, VariableType.STOCK, equation_func=self._v03_equation)
        # V04: Investimento EE (R$/mês) - Estoque
        self.v04 = SimVariable("V04", 3000000, VariableType.STOCK, equation_func=self._v04_equation)
        # V05: Gestão de Energia (0–1) - Auxiliar
        self.v05 = SimVariable("V05", 0, VariableType.AUXILIARY, equation_func=self._v05_equation)
        # V06: Barreiras (0–1) - Auxiliar
        self.v06 = SimVariable("V06", 0, VariableType.AUXILIARY, equation_func=self._v06_equation)
        # V07: Custos Operacionais (R$/mês) - Auxiliar
        self.v07 = SimVariable("V07", 0, VariableType.AUXILIARY, equation_func=self._v07_equation)
        # V08: Informação (0–1) - Auxiliar
        self.v08 = SimVariable("V08", 0, VariableType.AUXILIARY, equation_func=self._v08_equation)
        # V09: Produção (R$/mês) - Estoque
        self.v09 = SimVariable("V09", 450000000, VariableType.STOCK, equation_func=self._v09_equation)
        # V10: Crédito (0–1) - Auxiliar
        self.v10 = SimVariable("V10", 0, VariableType.AUXILIARY, equation_func=self._v10_equation)
        # V11: Competitividade (0–1) - Auxiliar
        self.v11 = SimVariable("V11", 0, VariableType.AUXILIARY, equation_func=self._v11_equation)
        # V14: Políticas (0–1) - Constant (already covered by POLITICAS parameter)
        self.v14 = SimVariable("V14", 0.55, VariableType.CONSTANT) # Explicitly define as constant for clarity
        # V16: Capacitação (0–1) - Auxiliar
        self.v16 = SimVariable("V16", 0, VariableType.AUXILIARY, equation_func=self._v16_equation)
        # V17: Autogeração (MWh/mês) - Auxiliar
        self.v17 = SimVariable("V17", 0, VariableType.AUXILIARY, equation_func=self._v17_equation)
        # V18: ICMS Energia (R$/mês) - Auxiliar
        self.v18 = SimVariable("V18", 0, VariableType.AUXILIARY, equation_func=self._v18_equation)
        # V20: ICMS EE (R$/mês) - Auxiliar
        self.v20 = SimVariable("V20", 0, VariableType.AUXILIARY, equation_func=self._v20_equation)
        # V21: ICMS Total (R$/mês) - Auxiliar
        self.v21 = SimVariable("V21", 0, VariableType.AUXILIARY, equation_func=self._v21_equation)
        # V22: Financiamento Verde (0–1) - Constant (already covered by FIN_GREEN parameter)
        self.v22 = SimVariable("V22", 0.65, VariableType.CONSTANT) # Explicitly define as constant for clarity
        # V29: ICMS Insumos (R$/mês) - Auxiliar
        self.v29 = SimVariable("V29", 0, VariableType.AUXILIARY, equation_func=self._v29_equation)

    # --- Equation Functions for Variables ---

    @staticmethod
    def _v01_equation(self_var: SimVariable, vars: Any) -> float:
        """V01 = θ1·V09·(1 − η·V03) − V17 + rebote_frac·η·V03·θ1·V09"""
        
        # V01 = θ1·V09·(1 − η·V03) − V17 + rebote_frac·η·V03·θ1·V09
        return vars.theta1.v * vars.v09.v * (1 - vars.eta.v * vars.v03.v) - \
               vars.v17.v + vars.rebote_frac.v * vars.eta.v * vars.v03.v * vars.theta1.v * vars.v09.v

    @staticmethod
    def _v03_equation(self_var: SimVariable, vars: Any) -> float:
        """dV03/dt = k_eff_inv·V04 + k_eff_sge·V05 + k_eff_cap·V16 − k_eff_bar·V06"""
        return vars.k_eff_inv.v * vars.v04.v + \
               vars.k_eff_sge.v * vars.v05.v + \
               vars.k_eff_cap.v * vars.v16.v - \
               vars.k_eff_bar.v * vars.v06.v

    @staticmethod
    def _v04_equation(self_var: SimVariable, vars: Any) -> float:
        """dV04/dt = 5e6·V10 + 1.5e6·V14 + 2.5e6·V08"""
        return 5e6 * vars.v10.v + \
               1.5e6 * vars.v14.v + \
               2.5e6 * vars.v08.v

    @staticmethod
    def _v05_equation(self_var: SimVariable, vars: Any) -> float:
        """V05 = k_eff_sge·V14 + k_eff_cap·V16"""
        return vars.k_eff_sge.v * vars.v14.v + \
               vars.k_eff_cap.v * vars.v16.v

    @staticmethod
    def _v06_equation(self_var: SimVariable, vars: Any) -> float:
        """V06 = 1 − (k_bar_pol·V14 + k_bar_info·V08 + k_bar_cred·V10)"""
        return 1 - (vars.k_bar_pol.v * vars.v14.v + \
                   vars.k_bar_info.v * vars.v08.v + \
                   vars.k_bar_cred.v * vars.v10.v)

    @staticmethod
    def _v07_equation(self_var: SimVariable, vars: Any) -> float:
        """V07 = θ_en_cost·V01·V02 + θ_ineff·(1 − V03)"""
        return vars.theta_en_cost.v * vars.v01.v * vars.v02.v + \
               vars.theta_ineff.v * (1 - vars.v03.v)

    @staticmethod
    def _v08_equation(self_var: SimVariable, vars: Any) -> float:
        """V08 = k_info_cap·V16 + k_info_pol·V14 − k_info_bar·V06 + 0.4"""
        return vars.k_info_cap.v * vars.v16.v + \
               vars.k_info_pol.v * vars.v14.v - \
               vars.k_info_bar.v * vars.v06.v + 0.4

    @staticmethod
    def _v09_equation(self_var: SimVariable, vars: Any) -> float:
        """dV09/dt = θ_prod_comp·V11 − θ_prod_cost·V07"""
        return vars.theta_prod_comp.v * vars.v11.v - \
               vars.theta_prod_cost.v * vars.v07.v

    @staticmethod
    def _v10_equation(self_var: SimVariable, vars: Any) -> float:
        """V10 = k_cred_green·V22 + k_cred_pol·V14"""
        return vars.k_cred_green.v * vars.v22.v + \
               vars.k_cred_pol.v * vars.v14.v

    @staticmethod
    def _v11_equation(self_var: SimVariable, vars: Any) -> float:
        """V11 = 1 / (1 + exp(−(k_comp_eff·V03 − k_comp_cost·V07)))"""
        return 1 / (1 + math.exp(-(vars.k_comp_eff.v * vars.v03.v - \
                                   vars.k_comp_cost.v * vars.v07.v)))

    @staticmethod
    def _v16_equation(self_var: SimVariable, vars: Any) -> float:
        """V16 = V14"""
        return vars.v14.v

    @staticmethod
    def _v17_equation(self_var: SimVariable, vars: Any) -> float:
        """V17 = k_gd_inv·V04 + k_gd_pol·V14·800"""
        return vars.k_gd_inv.v * vars.v04.v + \
               vars.k_gd_pol.v * vars.v14.v * 800

    @staticmethod
    def _v18_equation(self_var: SimVariable, vars: Any) -> float:
        """V18 = τ·V02·V01"""
        return vars.ICMS_TAU.v * vars.v02.v * vars.v01.v

    @staticmethod
    def _v20_equation(self_var: SimVariable, vars: Any) -> float:
        """V20 = β_ICMS_EE·V04"""
        return vars.beta_ICMS_EE.v * vars.v04.v

    @staticmethod
    def _v21_equation(self_var: SimVariable, vars: Any) -> float:
        """V21 = V18 + V20 + V29"""
        return vars.v18.v + vars.v20.v + vars.v29.v

    @staticmethod
    def _v29_equation(self_var: SimVariable, vars: Any) -> float:
        """V29 = δ_ICMS_insumos·V09"""
        return vars.delta_ICMS_insumos.v * vars.v09.v

if __name__ == "__main__":
    # Create an instance of the model
    model = FapergsRGEModel()

    # Create and run the simulation
    sim = Simulation(model, time_steps=120, dt=1.0)
    print("Executing FapergsRGEModel simulation...")
    sim.run()

    # Print results
    print("\n--- Final Results ---")
    for name, var in sim._variables.items():
        print(f"{name} (final): {var.v:.2f}, History: {var.history}")

    # Generate and print the dependency graph
    print("\n--- Dependency Graph ---")
    dependencies_graph = sim.get_dependencies_graph()
    for target, sources in dependencies_graph.items():
        print(f"{target} depends on: {sources}")
