"""
Docstring for v5_2.orchestra.client
It handles client-side operations and functionalities.
"""

"""
    / [GET]                     home
    /receive [POST]             receive response (from server)    
"""

"""
Flow of operations:

- Wake; register `/register` endpoint
- Wait for tasks at `/receive` endpoint
- Post results to receipt url.

---

Tooling:

1. Open Process; 
2. Start Flask server to listen for incoming requests (on the process)
3. Register (with ID)
4. Wait for jobs
5. Respond 

The flask server responds with receipts and passes the job
to your handler. This is done through process-level communication.

When work is done, post it back to the server.
A Message has a receipt URL (likely the server). 

To keep it clean, the _receipt_ data is in the headers, allowing
the body to be pure data.

"""

# Run flask client process to receive messages
# Give it a pipes we can send and receive messages through
# the flash client server process will push messages to the main process
# The main process will handle them and send back results
# The client server process will send receipts back to the server

from multiprocessing import Process, Pipe


def client_server(conn):
    """The client server process that runs Flask and communicates via pipe."""
    while True:
        # Wait for messages from the main process
        if conn.poll():
            msg = conn.recv()
            if msg == 'SHUTDOWN':
                break
            # Handle incoming work here
            print(f"[client_server] Received: {msg}")


def main():
    """Main entry point - starts the client server process with pipes."""
    # Create a pipe for bidirectional communication
    parent_conn, child_conn = Pipe()
    
    # Start the client server process
    process = Process(target=client_server, args=(child_conn,))
    process.start()
    
    print("[main] Client server process started")
    
    try:
        # Main loop - handle work and communicate with client_server
        while True:
            pass  # TODO: Add main process logic
    except KeyboardInterrupt:
        print("\n[main] Shutting down...")
        parent_conn.send('SHUTDOWN')
        process.join()
        print("[main] Client server process terminated")


if __name__ == '__main__':
    main()


