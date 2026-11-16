
import queue
import threading


class SharedState:

    def __init__(self):

        # Queues connecting manufacturing stages
        self.assembly_queue = queue.Queue()
        self.urgent_queue = queue.Queue()
        self.testing_queue = queue.Queue()
        self.packaging_queue = queue.Queue()
        self.discard_queue = queue.Queue()

        # Thread synchronization
        self.stop_event = threading.Event()
        self.assembly_done = threading.Event()

        self.urgent_lock = threading.Lock()
        self.id_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        self.inventory_lock = threading.RLock()

        # Circuit identification
        self.circuit_counter = 0

        # Immediate testing requests
        self.urgent_requests = 0

        # Worker statistics
        self.worker_stats = {
            f"Assembly-{i}": {
                "assembled": 0,
                "failed": 0
            }
            for i in range(1, 6)
        }

        # Finished inventory
        self.inventory = {}
        self.pending_by_inspector = {}

        self.box_counter = 0

    def reset_run(self):

        self.stop_event.clear()
        self.assembly_done.clear()

        with self.urgent_lock:
            self.urgent_requests = 0

    def new_circuit_id(self):

        with self.id_lock:
            self.circuit_counter += 1

            return f"C{self.circuit_counter:06d}"

    def record_assembled(self, worker):

        with self.stats_lock:
            self.worker_stats[worker]["assembled"] += 1

    def record_failure(self, worker):

        with self.stats_lock:
            self.worker_stats[worker]["failed"] += 1

    def request_urgent(self):

        with self.urgent_lock:
            self.urgent_requests += 1

    def submit_circuit(self, circuit):

        with self.urgent_lock:

            if self.urgent_requests > 0:

                self.urgent_requests -= 1

                self.urgent_queue.put(circuit)

                print(
                    f"URGENT: {circuit.circuit_id} "
                    f"sent directly to testing"
                )

            else:

                self.assembly_queue.put(circuit)

    def new_box_number(self):

        with self.inventory_lock:
            self.box_counter += 1

            return self.box_counter

