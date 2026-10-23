import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from queue import Queue

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


ASSEMBLY_WORKERS = 5
TESTING_WORKERS = 3
PACKAGING_WORKERS = 2
TRAY_CAPACITY = 13
BOX_CAPACITY = 5
FAILURE_RATE = 0.025
@dataclass
class Circuit:
    circuit_id: int
    components: tuple[str, ...] = (
        "resistor",
        "inductor",
        "capacitor",
        "voltage source",
    )
    inspector: str | None = None
    _mark_lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )
    assembler: str = "Unknown"

    def mark_inspected(self, inspector: str) -> None:
        with self._mark_lock:
            self.inspector = inspector

    def get_inspector(self) -> str | None:
        with self._mark_lock:
            return self.inspector


@dataclass(frozen=True)
class Box:
    inspector: str
    box_number: int
    circuits: tuple[Circuit, ...]


class Factory:
    def __init__(self) -> None:
        self._assembly_condition = threading.Condition()
        self._assembled: deque[Circuit] = deque()
        self._expedite_targets: deque[int] = deque()
        self._next_circuit_id = 1
        self._tray: list[Circuit] = []

        self._testing_queue: Queue[Circuit | None] = Queue()
        self._good_circuits: Queue[Circuit | None] = Queue()
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()
        self._active = False
        self._assembly_threads: list[threading.Thread] = []
        self._testing_threads: list[threading.Thread] = []
        self._packaging_threads: list[threading.Thread] = []
        self._overseer_thread: threading.Thread | None = None

        self._inventory_lock = threading.Lock()
        self._inventory: dict[str, list[Box]] = defaultdict(list)

        self._metrics_lock = threading.Lock()
        self._good_circuits_count = 0
        self._bad_circuits_count = 0
        self._bad_circuits: list[tuple[int, str]] = []
        self._assembled_by_worker = {
            f"Assembler-{worker_number}": 0
            for worker_number in range(1, ASSEMBLY_WORKERS + 1)
        }
        self._failed_by_worker = {
            f"Assembler-{worker_number}": 0
            for worker_number in range(1, ASSEMBLY_WORKERS + 1)
        }
        self._production_time_total = 0.0
        self._production_time_count = 0
        self._testing_time_total = 0.0
        self._testing_time_count = 0
        self._packaging_time_total = 0.0
        self._packaging_time_count = 0

    @property
    def is_active(self) -> bool:
        with self._state_lock:
            return self._active

    def begin(self) -> None:
        with self._state_lock:
            if self._active:
                print("Production is already running.")
                return
            self._active = True

        self._stop_event.clear()
        with self._assembly_condition:
            self._expedite_targets.clear()
        self._assembly_threads = [
            threading.Thread(
                target=self._assembly_worker,
                args=(worker_number,),
                name=f"Assembler-{worker_number}",
            )
            for worker_number in range(1, ASSEMBLY_WORKERS + 1)
        ]
        self._testing_threads = [
            threading.Thread(
                target=self._testing_worker,
                args=(worker_number,),
                name=f"Inspector-{worker_number}",
            )
            for worker_number in range(1, TESTING_WORKERS + 1)
        ]
        self._overseer_thread = threading.Thread(
            target=self._overseer, name="Assembly-Overseer"
        )

        for worker in self._testing_threads:
            worker.start()
        self._overseer_thread.start()
        for worker in self._assembly_threads:
            worker.start()

        self._start_packagers()

        print("Production started.")

    def halt(self) -> None:
        with self._state_lock:
            if not self._active:
                print("Production is not running.")
                return
            self._active = False

        self._stop_event.set()
        for worker in self._assembly_threads:
            worker.join()

        with self._assembly_condition:
            self._assembly_condition.notify_all()

        # The overseer flushes the partial assembly tray before it exits.
        if self._overseer_thread is not None:
            self._overseer_thread.join()

        for _ in self._testing_threads:
            self._testing_queue.put(None)
        for worker in self._testing_threads:
            worker.join()

        self._stop_packagers()
        print("Production halted; all assembled circuits have been tested.")

    def inventory_report(self) -> None:
        with self._inventory_lock:
            inventory = {
                inspector: tuple(boxes)
                for inspector, boxes in self._inventory.items()
            }

        if not inventory:
            print("No boxed circuits are in inventory.")
            return

        inspectors = ("Inspector-1", "Inspector-2", "Inspector-3")
        columns: list[list[str]] = []
        for inspector in inspectors:
            cells: list[str] = []
            for box in inventory.get(inspector, ()):
                board_ids = ", ".join(
                    str(circuit.circuit_id) for circuit in box.circuits
                )
                cells.append(f"Box {box.box_number}: circuits {board_ids}")
            columns.append(cells)

        widths = [
            max([len(inspector), *(len(cell) for cell in cells)])
            for inspector, cells in zip(inspectors, columns)
        ]
        print(
            " | ".join(
                inspector.ljust(width)
                for inspector, width in zip(inspectors, widths)
            )
        )
        print("-+-".join("-" * width for width in widths))

        for row in range(max(map(len, columns), default=0)):
            print(
                " | ".join(
                    (cells[row] if row < len(cells) else "").ljust(width)
                    for cells, width in zip(columns, widths)
                )
            )

    def report(self) -> None:
        with self._metrics_lock:
            good_circuits = self._good_circuits_count
            bad_circuits = self._bad_circuits_count
            bad_circuits_detail = tuple(self._bad_circuits)
            production_time_total = self._production_time_total
            production_time_count = self._production_time_count
            testing_time_total = self._testing_time_total
            testing_time_count = self._testing_time_count
            packaging_time_total = self._packaging_time_total
            packaging_time_count = self._packaging_time_count

        print("Production report")
        print(f"Total good circuits: {good_circuits}")
        print(f"Total bad circuits: {bad_circuits}")
        print("Failed circuits by assembly worker:")
        assemblers = [
            f"Assembler-{worker_number}"
            for worker_number in range(1, ASSEMBLY_WORKERS + 1)
        ]
        circuits_by_assembler = {
            assembler: [] for assembler in assemblers
        }
        for circuit_id, assembler in bad_circuits_detail:
            circuits_by_assembler[assembler].append(f"Circuit {circuit_id}")

        columns = [circuits_by_assembler[assembler] for assembler in assemblers]
        widths = [
            max([len(assembler), *(len(circuit) for circuit in circuits)])
            for assembler, circuits in zip(assemblers, columns)
        ]
        print(
            " | ".join(
                assembler.ljust(width)
                for assembler, width in zip(assemblers, widths)
            )
        )
        print("-+-".join("-" * width for width in widths))
        if bad_circuits_detail:
            for row in range(max(map(len, columns), default=0)):
                print(
                    " | ".join(
                        (circuits[row] if row < len(circuits) else "").ljust(width)
                        for circuits, width in zip(columns, widths)
                    )
                )
        else:
            print(" | ".join("None".ljust(width) for width in widths))

        if (
            production_time_count
            and testing_time_count
            and packaging_time_count
        ):
            combined_average = (
                production_time_total / production_time_count
                + testing_time_total / testing_time_count
                + packaging_time_total / packaging_time_count
            )
            print(
                "Average combined time (produce, test, and package): "
                f"{combined_average:.2f} seconds"
            )
        else:
            print(
                "Average combined time (produce, test, and package): "
                "N/A (no completed circuits)"
            )

    def graph(self) -> None:
        with self._metrics_lock:
            worker_results = tuple(
                (
                    worker,
                    self._failed_by_worker[worker],
                    self._assembled_by_worker[worker],
                )
                for worker in self._assembled_by_worker
            )

        failure_rates = [
            failed / assembled if assembled else 0.0
            for _, failed, assembled in worker_results
        ]
        workers = [worker for worker, _, _ in worker_results]

        figure, axis = plt.subplots()
        bars = axis.bar(workers, failure_rates)
        axis.set_title("Failure Rate per Assembly Worker")
        axis.set_xlabel("Assembly Worker")
        axis.set_ylabel("Failure Rate")
        axis.yaxis.set_major_formatter(PercentFormatter(1.0))
        axis.set_ylim(0, max(failure_rates, default=0.0) * 1.2 or 0.01)

        label_offset = axis.get_ylim()[1] * 0.02
        for bar, (_, failed, assembled), rate in zip(
            bars, worker_results, failure_rates
        ):
            label = f"{rate:.2%}\n({failed}/{assembled})" if assembled else "N/A"
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + label_offset,
                label,
                ha="center",
                va="bottom",
            )

        figure.tight_layout()
        plt.show()

    def spotcheck(
        self, inspector: str, box_number: int, circuit_id: int
    ) -> None:
        inspector_name = (
            f"Inspector-{inspector}" if inspector.isdecimal() else inspector
        )
        with self._inventory_lock:
            boxes = self._inventory.get(inspector_name, [])
            box = next(
                (item for item in boxes if item.box_number == box_number), None
            )
            if box is None:
                print(f"No box {box_number} for inspector {inspector_name}.")
                return
            circuit = next(
                (item for item in box.circuits if item.circuit_id == circuit_id),
                None,
            )
            if circuit is None:
                print(f"Circuit {circuit_id} is not in box {box_number}.")
                return

        marked_inspector = circuit.get_inspector()
        if marked_inspector == inspector_name:
            print(
                f"Spotcheck passed: circuit {circuit.circuit_id} is marked "
                f"{marked_inspector}."
            )
        else:
            print(
                f"Spotcheck failed: expected {inspector_name}, found "
                f"{marked_inspector or 'no inspector mark'}."
            )

    def _assembly_worker(self, worker_number: int) -> None:
        while not self._stop_event.is_set():
            started_at = time.perf_counter()
            assembly_time = max(0.01, random.gauss(11, 2))
            if self._stop_event.wait(assembly_time):
                break
            elapsed = time.perf_counter() - started_at

            with self._assembly_condition:
                circuit = Circuit(
                    self._next_circuit_id,
                    assembler=f"Assembler-{worker_number}",
                )
                self._next_circuit_id += 1
                self._assembled.append(circuit)
                self._assembly_condition.notify()
            with self._metrics_lock:
                self._production_time_total += elapsed
                self._production_time_count += 1
                self._assembled_by_worker[f"Assembler-{worker_number}"] += 1

    def _overseer(self) -> None:
        while True:
            with self._assembly_condition:
                while not self._assembled and not self._stop_event.is_set():
                    self._assembly_condition.wait()

                if not self._assembled:
                    if self._stop_event.is_set():
                        if self._tray:
                            for circuit in self._tray:
                                self._testing_queue.put(circuit)
                            self._tray = []
                        return
                    continue

                circuit = self._assembled.popleft()
                expedited = bool(
                    self._expedite_targets
                    and self._expedite_targets[0] <= circuit.circuit_id
                )
                if expedited:
                    self._expedite_targets.popleft()
                    if (
                        self._expedite_targets
                        and self._expedite_targets[0] <= circuit.circuit_id
                    ):
                        self._expedite_targets[0] = circuit.circuit_id + 1

                if not expedited:
                    self._tray.append(circuit)
                    if len(self._tray) < TRAY_CAPACITY:
                        continue
                    tray = self._tray
                    self._tray = []
                else:
                    tray = [circuit]

            for circuit in tray:
                self._testing_queue.put(circuit)

    def _request_expedited_circuit(self) -> None:
        with self._assembly_condition:
            self._expedite_targets.append(self._next_circuit_id)
            self._assembly_condition.notify()

    def _testing_worker(self, worker_number: int) -> None:
        inspector = f"Inspector-{worker_number}"
        while True:
            work = self._testing_queue.get()
            if work is None:
                self._testing_queue.task_done()
                return

            circuit = work
            started_at = time.perf_counter()
            test_time = max(0.01, random.gauss(6, 1))
            # Halt interrupts the simulated delay while still draining work.
            self._stop_event.wait(test_time)
            elapsed = time.perf_counter() - started_at

            failed = random.random() < FAILURE_RATE
            if failed:
                self._request_expedited_circuit()
            else:
                circuit.mark_inspected(inspector)

            with self._metrics_lock:
                if failed:
                    self._bad_circuits_count += 1
                    self._bad_circuits.append(
                        (circuit.circuit_id, circuit.assembler)
                    )
                    self._failed_by_worker[circuit.assembler] += 1
                else:
                    self._good_circuits_count += 1
                    self._good_circuits.put(circuit)
                self._testing_time_total += elapsed
                self._testing_time_count += 1

            self._testing_queue.task_done()

    def _packager_worker(self) -> None:
        circuits_by_inspector: dict[str, list[Circuit]] = defaultdict(list)
        while True:
            work = self._good_circuits.get()
            if work is None:
                self._good_circuits.task_done()
                return

            circuit = work
            inspector = circuit.get_inspector()
            if inspector is None:
                self._good_circuits.task_done()
                raise RuntimeError(
                    f"Circuit {circuit.circuit_id} has no inspector mark."
                )

            started_at = time.perf_counter()
            inspector_circuits = circuits_by_inspector[inspector]
            inspector_circuits.append(circuit)
            if len(inspector_circuits) == BOX_CAPACITY:
                # Spec: grabbing and boxing 5 circuits takes ~2 s (std dev 0.25 s)
                self._stop_event.wait(max(0.01, random.gauss(2, 0.25)))
                boxed_circuits = tuple(inspector_circuits)
                with self._inventory_lock:
                    box_number = len(self._inventory[inspector]) + 1
                    self._inventory[inspector].append(
                        Box(inspector, box_number, boxed_circuits)
                    )
                circuits_by_inspector[inspector] = []
            elapsed = time.perf_counter() - started_at
            with self._metrics_lock:
                self._packaging_time_total += elapsed
                self._packaging_time_count += 1

            self._good_circuits.task_done()

    def _start_packagers(self) -> None:
        self._packaging_threads = [
            threading.Thread(
                target=self._packager_worker,
                name=f"Packager-{worker_number}",
            )
            for worker_number in range(1, PACKAGING_WORKERS + 1)
        ]
        for worker in self._packaging_threads:
            worker.start()

    def _stop_packagers(self) -> None:
        for _ in self._packaging_threads:
            self._good_circuits.put(None)
        for worker in self._packaging_threads:
            worker.join()


def main() -> None:
    factory = Factory()
    print(
        "Commands: begin, halt, inventory, report, graph, spotcheck, "
        "spotcheck <inspector> <box> <circuit ID>, exit"
    )

    while True:
        try:
            command_line = input("> ").strip()
        except EOFError:
            if factory.is_active:
                factory.halt()
            print()
            return

        if not command_line:
            continue

        command, *arguments = command_line.split()
        command = command.lower()

        if command == "begin":
            factory.begin()
        elif command == "halt":
            factory.halt()
        elif command == "inventory":
            factory.inventory_report()
        elif command == "report":
            factory.report()
        elif command == "graph":
            factory.graph()
        elif command == "spotcheck":
            if not arguments:
                inspector = input("Inspector name: ").strip()
                box_input = input("Box number: ").strip()
                circuit_input = input("Circuit ID: ").strip()
            elif len(arguments) == 3:
                inspector, box_input, circuit_input = arguments
            else:
                print(
                    "Usage: spotcheck <inspector> <box number> <circuit ID>"
                )
                continue

            try:
                factory.spotcheck(inspector, int(box_input), int(circuit_input))
            except ValueError:
                print("Box number and circuit ID must be integers.")
        elif command == "exit":
            if factory.is_active:
                factory.halt()
            return
        else:
            print(
                "Unknown command. Enter begin, halt, inventory, report, "
                "graph, spotcheck, or exit."
            )


if __name__ == "__main__":
    main()
