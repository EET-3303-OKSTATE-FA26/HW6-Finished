
def show_inventory(shared):

    with shared.inventory_lock:

        inventory = {
            inspector: list(boxes)
            for inspector, boxes in shared.inventory.items()
        }

        pending = {
            inspector: list(circuits)
            for inspector, circuits in shared.pending_by_inspector.items()
        }

    print("\n========== INVENTORY REPORT ==========")

    for inspector, boxes in inventory.items():

        print(f"\nInspector: {inspector}")

        for box in sorted(boxes, key=lambda b: b.box_number):

            print(f"\nBox Number: {box.box_number}")

            for i, circuit in enumerate(box.circuits, 1):

                print(
                    f"Board {i}: {circuit.circuit_id} "
                    f"| Assembly Worker: {circuit.assembly_worker}"
                )

    print("\n========== UNBOXED CIRCUITS ==========")

    for inspector, circuits in pending.items():

        if circuits:

            print(f"\n{inspector}: {len(circuits)} circuits")

    print("\n======================================\n")


def spot_check(shared, expected_inspector, box_number, board_number):

    if board_number < 1 or board_number > 5:

        print("Invalid board number. Boxes contain 5 boards.")
        return

    with shared.inventory_lock:

        selected_box = None

        for inspector, boxes in shared.inventory.items():

            for box in boxes:

                if box.box_number == box_number:
                    selected_box = box
                    break

            if selected_box is not None:
                break

    if selected_box is None:

        print("Box not found.")
        return

    circuit = selected_box.circuits[board_number - 1]

    with circuit.lock:
        actual_inspector = circuit.inspector

    print("\n========== SPOT CHECK ==========")

    print(f"Box Number: {box_number}")
    print(f"Board Number: {board_number}")
    print(f"Circuit ID: {circuit.circuit_id}")

    print(f"Expected Inspector: {expected_inspector}")
    print(f"Actual Inspector: {actual_inspector}")

    if actual_inspector == expected_inspector:

        print("RESULT: Inspector mark matches.")

    else:

        print("RESULT: INSPECTOR MISMATCH!")

    print("================================\n")


def show_failure_report(shared):

    import matplotlib.pyplot as plt

    with shared.stats_lock:

        stats = {
            worker: values.copy()
            for worker, values in shared.worker_stats.items()
        }

    workers = []
    failure_rates = []

    print("\n========== FAILURE REPORT ==========")

    for worker, values in stats.items():

        assembled = values["assembled"]
        failed = values["failed"]

        if assembled > 0:
            rate = (failed / assembled) * 100
        else:
            rate = 0

        workers.append(worker)
        failure_rates.append(rate)

        print(
            f"{worker}: {failed}/{assembled} failed "
            f"({rate:.2f}%)"
        )

    print("===================================\n")

    plt.figure(figsize=(9, 5))

    plt.bar(workers, failure_rates)

    plt.xlabel("Assembly Worker")
    plt.ylabel("Failure Rate (%)")

    plt.title("Circuit Failure Rate Per Assembly Worker")

    plt.ylim(bottom=0)

    plt.tight_layout()

    plt.show()
