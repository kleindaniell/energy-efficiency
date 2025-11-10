from typing import Dict, List, Tuple, Optional, Callable
import numpy as np
from dataclasses import dataclass
from enum import Enum
import math

class VariableType(Enum):
    STOCK = "stock"
    FLOW = "flow"
    AUXILIARY = "auxiliary"
    CONSTANT = "constant"

class InfluenceMode(Enum):
    LINEAR = "linear"
    LOGISTIC = "logistic"
    SATURATION = "saturation"
    EXPONENTIAL = "exponential"
    THRESHOLD = "threshold"
    DELAY = "delay"

@dataclass
class Influence:
    """Represents an influence from one variable to another."""
    source_var: 'SimVariable'
    weight: float = 1.0
    mode: InfluenceMode = InfluenceMode.LINEAR
    delay: int = 0
    threshold: float = 0.0
    
    def __post_init__(self):
        self.delay_buffer: List[float] = []
    
    def calculate_delta(self, source_value: float) -> float:
        """Calculate the delta contribution from this influence."""
        if self.delay > 0:
            self.delay_buffer.append(source_value)
            if len(self.delay_buffer) > self.delay:
                delayed_value = self.delay_buffer.pop(0)
            else:
                delayed_value = self.delay_buffer[0] if self.delay_buffer else 0.0
        else:
            delayed_value = source_value
        
        if self.mode == InfluenceMode.LINEAR:
            return self.weight * delayed_value
        elif self.mode == InfluenceMode.LOGISTIC:
            return self.weight * delayed_value / (1 + abs(delayed_value))
        elif self.mode == InfluenceMode.SATURATION:
            return self.weight * (1 - math.exp(-abs(delayed_value)))
        elif self.mode == InfluenceMode.EXPONENTIAL:
            return self.weight * delayed_value * abs(delayed_value)
        elif self.mode == InfluenceMode.THRESHOLD:
            return self.weight * delayed_value if delayed_value > self.threshold else 0.0
        return 0.0

class SimVariable:
    """Represents a variable in the system dynamics model."""
    
    def __init__(self, name: str, initial_value: float = 0.0, 
                 var_type: VariableType = VariableType.STOCK,
                 accept_negative: bool = True, min_value: Optional[float] = None,
                 max_value: Optional[float] = None,
                 auxiliary_func: Optional[Callable] = None):
        self.name = name
        self.initial_value = initial_value
        self.value = initial_value
        self.var_type = var_type
        self.history: List[float] = [initial_value]
        self.influences: List[Influence] = []
        self.accept_negative = accept_negative
        self.min_value = min_value
        self.max_value = max_value
        self.auxiliary_func = auxiliary_func
        
        self.inflows: List['SimVariable'] = []
        self.outflows: List['SimVariable'] = []
        
        if not accept_negative and min_value is None:
            self.min_value = 0.0

    def add_influence(self, source_var: 'SimVariable', weight: float = 1.0, 
                     mode: InfluenceMode = InfluenceMode.LINEAR,
                     delay: int = 0, threshold: float = 0.0) -> None:
        """Add an influence from another variable."""
        influence = Influence(source_var, weight, mode, delay, threshold)
        self.influences.append(influence)
    
    def add_inflow(self, flow_var: 'SimVariable') -> None:
        """Add an inflow (for stock variables)."""
        self.inflows.append(flow_var)
    
    def add_outflow(self, flow_var: 'SimVariable') -> None:
        """Add an outflow (for stock variables)."""
        self.outflows.append(flow_var)
    
    def calculate_delta(self) -> float:
        """Calculate the total change for this time step."""
        if self.var_type == VariableType.CONSTANT:
            return 0.0
        
        if self.var_type == VariableType.AUXILIARY and self.auxiliary_func:
            return 0.0
        
        total_delta = 0.0
        
        if self.var_type == VariableType.STOCK:
            for inflow in self.inflows:
                total_delta += inflow.value
            for outflow in self.outflows:
                total_delta -= outflow.value
        
        for influence in self.influences:
            delta = influence.calculate_delta(influence.source_var.value)
            total_delta += delta
            
        return total_delta
    
    def update(self, dt: float) -> None:
        """Update the variable's value based on influences."""
        if self.var_type == VariableType.CONSTANT:
            return
        
        if self.var_type == VariableType.AUXILIARY and self.auxiliary_func:
            self.value = self.auxiliary_func(self)
        else:
            delta = self.calculate_delta()
            new_value = self.value + delta * dt
            
            if self.min_value is not None:
                new_value = max(self.min_value, new_value)
            if self.max_value is not None:
                new_value = min(self.max_value, new_value)
                
            self.value = new_value
            
        self.history.append(self.value)
    
    def get_rate_of_change(self) -> float:
        """Get current rate of change (derivative)."""
        if len(self.history) < 2:
            return 0.0
        return self.history[-1] - self.history[-2]
    
    def reset(self) -> None:
        """Reset variable to initial state."""
        self.value = self.initial_value
        self.history = [self.initial_value]
        for influence in self.influences:
            influence.delay_buffer = []

class Simulation:
    """System dynamics simulation engine."""
    
    def __init__(self, variables: Dict[str, SimVariable], 
                 time_steps: int = 50, dt: float = 1.0,
                 integration_method: str = "euler"):
        self.variables = variables
        self.time_steps = time_steps
        self.dt = dt
        self.current_step = 0
        self.integration_method = integration_method
        
        self.equilibrium_detection = True
        self.equilibrium_threshold = 1e-6
        self.equilibrium_window = 10
        
    def step(self) -> None:
        """Execute one simulation step."""
        if self.current_step >= self.time_steps - 1:
            return
        
        if self.integration_method == "euler":
            self._euler_step()
        elif self.integration_method == "rk4":
            self._rk4_step()
        else:
            self._euler_step()
            
        self.current_step += 1
    
    def _euler_step(self) -> None:
        """Euler integration step."""
        for var in self.variables.values():
            var.update(self.dt)
    
    def _rk4_step(self) -> None:
        """Runge-Kutta 4th order integration (more accurate)."""
        original_values = {name: var.value for name, var in self.variables.items()}
        
        k1 = {}
        for name, var in self.variables.items():
            k1[name] = var.calculate_delta() * self.dt
        
        for name, var in self.variables.items():
            var.value = original_values[name] + k1[name] / 2
        k2 = {}
        for name, var in self.variables.items():
            k2[name] = var.calculate_delta() * self.dt
        
        for name, var in self.variables.items():
            var.value = original_values[name] + k2[name] / 2
        k3 = {}
        for name, var in self.variables.items():
            k3[name] = var.calculate_delta() * self.dt
        
        for name, var in self.variables.items():
            var.value = original_values[name] + k3[name]
        k4 = {}
        for name, var in self.variables.items():
            k4[name] = var.calculate_delta() * self.dt
        
        for name, var in self.variables.items():
            if var.var_type != VariableType.CONSTANT:
                new_value = original_values[name] + (k1[name] + 2*k2[name] + 2*k3[name] + k4[name]) / 6
                
                if var.min_value is not None:
                    new_value = max(var.min_value, new_value)
                if var.max_value is not None:
                    new_value = min(var.max_value, new_value)
                
                var.value = new_value
            var.history.append(var.value)
    
    def run(self) -> None:
        """Run the complete simulation."""
        self.reset()
        for step in range(self.time_steps - 1):
            self.step()
            
            if self.equilibrium_detection and self._check_equilibrium():
                print(f"Equilibrium reached at step {step + 1}")
                break
    
    def _check_equilibrium(self) -> bool:
        """Check if system has reached equilibrium."""
        if self.current_step < self.equilibrium_window:
            return False
        
        for var in self.variables.values():
            if var.var_type == VariableType.CONSTANT:
                continue
            
            recent_values = var.history[-self.equilibrium_window:]
            if len(recent_values) < self.equilibrium_window:
                return False
            
            max_change = max(abs(recent_values[i] - recent_values[i-1]) 
                           for i in range(1, len(recent_values)))
            if max_change > self.equilibrium_threshold:
                return False
        
        return True
    
    def sensitivity_analysis(self, var_name: str, parameter_range: Tuple[float, float], 
                           steps: int = 10) -> Dict[float, Dict[str, List[float]]]:
        """Perform sensitivity analysis on a variable."""
        results = {}
        original_value = self.variables[var_name].initial_value
        
        param_values = np.linspace(parameter_range[0], parameter_range[1], steps)
        
        for param_value in param_values:
            self.variables[var_name].initial_value = param_value
            self.run()
            results[param_value] = self.get_results()
        
        self.variables[var_name].initial_value = original_value
        return results
    
    def reset(self) -> None:
        """Reset simulation to initial state."""
        self.current_step = 0
        for var in self.variables.values():
            var.reset()
    
    def get_results(self) -> Dict[str, List[float]]:
        """Get simulation results as dictionary of histories."""
        return {name: var.history.copy() for name, var in self.variables.items()}
    
    def get_time_series(self) -> List[float]:
        """Get time series for plotting."""
        return [i * self.dt for i in range(len(next(iter(self.variables.values())).history))]
    
    def get_phase_space(self, var1_name: str, var2_name: str) -> Tuple[List[float], List[float]]:
        """Get phase space trajectory for two variables."""
        var1_history = self.variables[var1_name].history
        var2_history = self.variables[var2_name].history
        return var1_history, var2_history
