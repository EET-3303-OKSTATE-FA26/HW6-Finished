
import threading
import time
import random

from Circuit import Box


def packaging_worker(shared, worker_number):

    while True:

        circuit = shared.packaging_queue.get()

        if circuit is None:

            shared.packaging_queue.task_done()
            break

        try:

            # Safely read the inspector's mark
            with circuit.lock:
                inspector = circuit.inspector

            if inspector is None:
                print("ERROR: Circuit has no inspector mark.")
                continue

            box_to_package = None

            with shared.inventory_lock:

                if inspector not in shared.pending_by_inspector:

                    shared.pending_by_inspector[inspector] = []

                shared.pending_by_inspector[inspector].append(
                    circuit
                )

                # Package only when there are five
                if len(
                    shared.pending_by_inspector[inspector]
                ) >= 5:

                    circuits = (
                        shared.pending_by_inspector[inspector][:5]
                    )

                    del shared.pending_by_inspector[inspector][:5]

                    box_number = shared.new_box_number()

                    box_to_package = Box(
                        box_number,
                        inspector,
                        circuits
                    )

            if box_to_package is not None:

                packaging_time = max(
                    0.1,
                    random.normalvariate(2, 0.25)
                )

                time.sleep(packaging_time)

                with shared.inventory_lock:

                    if inspector not in shared.inventory:
                        shared.inventory[inspector] = []

                    shared.inventory[inspector].append(
                        box_to_package
                    )

                print(
                    f"Packager-{worker_number} finished "
                    f"Box {box_to_package.box_number} "
                    f"for {inspector}"
                )

        finally:

            shared.packaging_queue.task_done()


def start_packaging(shared):

    workers = []

    for i in range(1, 3):

        worker = threading.Thread(
            target=packaging_worker,
            args=(shared, i),
            name=f"Packager-{i}"
        )

        worker.start()

        workers.append(worker)

    return workers
