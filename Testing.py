
import threading
import time
import random


def testing_worker(shared, worker_number):

    inspector_name = f"Inspector-{worker_number}"

    while True:

        circuit = shared.testing_queue.get()

        if circuit is None:

            shared.testing_queue.task_done()
            break

        try:

            testing_time = max(
                0.1,
                random.normalvariate(6, 1)
            )

            time.sleep(testing_time)

            # Simulate the 2.5% failure rate
            if random.random() < 0.025:

                with circuit.lock:
                    circuit.is_defective = True

                shared.record_failure(
                    circuit.assembly_worker
                )

                shared.discard_queue.put(circuit)

                # Request the next assembled circuit
                # to be tested immediately
                shared.request_urgent()

                print(
                    f"FAILURE: {circuit.circuit_id} "
                    f"produced by {circuit.assembly_worker}"
                )

            else:

                # Safely write the inspector's name
                with circuit.lock:
                    circuit.inspector = inspector_name

                shared.packaging_queue.put(circuit)

                print(
                    f"{inspector_name} passed "
                    f"{circuit.circuit_id}"
                )

        finally:

            shared.testing_queue.task_done()


def start_testing(shared):

    workers = []

    for i in range(1, 4):

        worker = threading.Thread(
            target=testing_worker,
            args=(shared, i),
            name=f"Inspector-{i}"
        )

        worker.start()

        workers.append(worker)

    return workers
