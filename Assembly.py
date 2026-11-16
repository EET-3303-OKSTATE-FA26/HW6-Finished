
import threading
import time
import random
import queue

from Circuit import Circuit


def assembly_worker(shared, worker_number):

    worker_name = f"Assembly-{worker_number}"

    while not shared.stop_event.is_set():

        assembly_time = max(
            0.1,
            random.normalvariate(11, 2)
        )

        time.sleep(assembly_time)

        if shared.stop_event.is_set():
            break

        circuit_id = shared.new_circuit_id()

        circuit = Circuit(
            circuit_id,
            worker_name
        )

        shared.record_assembled(worker_name)

        shared.submit_circuit(circuit)

        print(
            f"{worker_name} assembled "
            f"{circuit.circuit_id}"
        )


def overseer(shared):

    batch = []

    while True:

        # Check for urgent circuits first
        try:

            circuit = shared.urgent_queue.get_nowait()

            shared.testing_queue.put(circuit)

            shared.urgent_queue.task_done()

            continue

        except queue.Empty:
            pass

        # Check whether production has finished
        if (
            shared.assembly_done.is_set()
            and shared.assembly_queue.empty()
            and shared.urgent_queue.empty()
        ):
            break

        # Collect regular circuits
        try:

            circuit = shared.assembly_queue.get(
                timeout=0.1
            )

            batch.append(circuit)

            shared.assembly_queue.task_done()

        except queue.Empty:
            continue

        # Send a full batch of 13
        if len(batch) == 13:

            print("Overseer: Tray full. Sending to testing.")

            for circuit in batch:
                shared.testing_queue.put(circuit)

            batch.clear()

    # Send any remaining circuits when production stops
    if batch:

        print(
            f"Overseer: Sending final batch "
            f"of {len(batch)} circuits."
        )

        for circuit in batch:
            shared.testing_queue.put(circuit)

    # Tell the three testing workers to stop
    for _ in range(3):
        shared.testing_queue.put(None)


def start_assembly(shared):

    overseer_thread = threading.Thread(
        target=overseer,
        args=(shared,),
        name="Overseer"
    )

    overseer_thread.start()

    workers = []

    for i in range(1, 6):

        worker = threading.Thread(
            target=assembly_worker,
            args=(shared, i),
            name=f"Assembly-{i}"
        )

        worker.start()

        workers.append(worker)

    return workers, overseer_thread
