
import threading
from dataclasses import dataclass, field


class Circuit:
    def __init__(self, circuit_id, assembly_worker):
        self.circuit_id = circuit_id
        self.assembly_worker = assembly_worker

        self.inspector = None
        self.is_defective = False

        # Circuit component values
        self.resistor = 100
        self.inductor = 0.01
        self.capacitor = 0.000001
        self.voltage_source = 10

        # Protects shared circuit information
        self.lock = threading.Lock()


@dataclass
class Box:
    box_number: int
    inspector: str
    circuits: list = field(default_factory=list)
