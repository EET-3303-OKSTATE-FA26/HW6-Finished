
from Shared import SharedState

from Assembly import start_assembly
from Testing import start_testing
from Packaging import start_packaging

from Inventory import (
    show_inventory,
    spot_check,
    show_failure_report
)


def begin_production(shared):

    shared.reset_run()

    print("\nStarting manufacturing process...\n")

    # Start packaging first
    packaging_workers = start_packaging(shared)

    # Start testing workers
    testing_workers = start_testing(shared)

    # Start assembly and overseer
    assembly_workers, overseer_thread = start_assembly(shared)

    print("Production has started!")

    return {
        "assembly": assembly_workers,
        "overseer": overseer_thread,
        "testing": testing_workers,
        "packaging": packaging_workers
    }


def halt_production(shared, threads):

    if threads is None:
        print("Production is not running.")
        return None

    print("\nStopping production...")

    # Stop assembly workers
    shared.stop_event.set()

    for worker in threads["assembly"]:
        worker.join()

    # Tell overseer assembly has finished
    shared.assembly_done.set()

    # Wait for overseer to finish sending circuits
    threads["overseer"].join()

    # Wait for all testing jobs to finish
    shared.testing_queue.join()

    for worker in threads["testing"]:
        worker.join()

    # Stop packaging workers
    for _ in threads["packaging"]:
        shared.packaging_queue.put(None)

    # Wait for packaging to finish
    shared.packaging_queue.join()

    for worker in threads["packaging"]:
        worker.join()

    print("\nProduction successfully stopped.")

    return None


def main():

    shared = SharedState()

    threads = None

    print("===================================")
    print(" ELECTRONIC CIRCUIT MANUFACTURING")
    print("===================================")

    print("\nAvailable Commands:")
    print("begin")
    print("halt")
    print("inventory")
    print("spotcheck")
    print("failures")
    print("exit")

    while True:

        command = input("\nEnter command: ").strip().lower()

        if command == "begin":

            if threads is not None:

                print("Production is already running.")

            else:

                threads = begin_production(shared)

        elif command == "halt":

            threads = halt_production(shared, threads)

        elif command == "inventory":

            show_inventory(shared)

        elif command == "spotcheck":

            try:

                inspector = input(
                    "Enter expected inspector name: "
                ).strip()

                box_number = int(
                    input("Enter box number: ")
                )

                board_number = int(
                    input("Enter board number (1-5): ")
                )

                spot_check(
                    shared,
                    inspector,
                    box_number,
                    board_number
                )

            except ValueError:

                print("Please enter valid numbers.")

        elif command == "failures":

            show_failure_report(shared)

        elif command == "exit":

            if threads is not None:

                threads = halt_production(shared, threads)

            print("Closing manufacturing simulation.")

            break

        else:

            print("Invalid command. Try again.")


if __name__ == "__main__":

    main()
