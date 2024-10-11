# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import asyncio
import os
import socket
import sys
import time
import traceback

# Weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None, # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def format_date_time(timestamp):
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )

DEV = LOGGING = False
if LOGGING:
    info = print
log = error = print


def create_socket(address):
    try:
        host, port = address.split(":")
        port = int(port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
    except OSError as e:
        error("Failed to create TCP Socket:", e)
        sys.exit(1)
    except ValueError:
        # https://pymotw.com/2/socket/uds.html
        path = os.path.normpath(os.path.abspath(address))
        try:
            os.unlink(path)
        except OSError:
            if os.path.exists(address):
                raise
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(path)
        os.chmod(path, 666)
    return sock


class BadRequest(Exception):
    pass


async def headers(reader):
    found = []
    counter = 0
    size = 0
    max_headers_length = 1024 * 1024
    while counter < 1000 and size < max_headers_length:
        line = await reader.readline()
        if LOGGING:
            info(line)
        if line == b"\r\n":
            # End of headers
            return found
        if len(line) < 4:
            raise BadRequest(f"Invalid header: {line}")
        size += len(line)
        counter += 1
        first = line.find(b":")
        if first < 0:
            raise BadRequest("Invalid header line")
        key = line[:first].lower().strip()
        value = line[first + 1 :].strip()
        found.append((key, value))
    raise BadRequest(
        f"Could not find end of headers after reading 1000 lines or {max_headers_length} bytes."
    )


def handle_connection(application):
    # https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
    async def handle_connection_run(reader, writer):
        try:
            while True:
                line = await reader.readline()
                if LOGGING:
                    info(line)
                if not line:
                    writer.close()
                    break
                try:
                    raw_method, raw_path, raw_http_version = line.strip().split(b" ")
                except Exception as e:
                    raise BadRequest(str(e))
                scope = {
                    "type": "http",
                    "asgi": {"version": "3.0", "spec_version": "2.3"},
                    "http_version": raw_http_version.decode("utf8")[5:],
                    "method": raw_method.decode("utf8").upper(),
                    "raw_path": raw_path,
                    "headers": await headers(reader),
                }
                pos = scope["raw_path"].find(b"?")
                if pos == 0:
                    raise BadRequest(
                        "Can't have a ? as the first character, should be /?"
                    )
                if pos > 0:
                    scope["path"] = scope["raw_path"][:pos].decode("utf8")
                    scope["query_string"] = scope["raw_path"][pos + 1 :]
                    # raise Exception((scope['path'], scope['query_string']))
                else:
                    scope["path"] = scope["raw_path"].decode("utf8")

                async def receive():
                    body = b""
                    for k, v in scope["headers"]:
                        if k == b"content-length":
                            body = await reader.read(int(v.decode("ascii")))
                    return {
                        "type": "http.request",
                        "body": body,
                        "more_body": False,
                    }

                started = [False]
                connection = [None]
                to_send = [b""]
                should_close = [False]

                for k, v in scope["headers"]:
                    if k.lower().strip() == b"connection":
                        connection[0] = v.lower()

                async def send(event):
                    if event["type"] == "http.response.start":
                        response = b"HTTP/1.1 " + str(event.get("status", 200)).encode('ascii') + b"\r\n"
                        started[0] = True
                        for k, v in event["headers"]:
                            response += k + b": " + v + b"\r\n"
                        if scope["http_version"] == "1.0":
                            if connection[0] == b"keep-alive":
                                response += b"Connection: Keep-Alive\r\n"
                            else:
                                should_close[0] = True
                        elif connection[0] == b"close":
                            response += b"Connection: Close\r\n"
                            should_close[0] = True
                        response += (
                            b"Date: "
                            + (format_date_time(time.time()).encode("utf8"))
                            + b"\r\n"
                        )
                        # response += b"Server: pyvicorn\r\n"
                        response += b"\r\n"
                        if LOGGING:
                            info(response)
                        to_send[0] += response
                    elif event["type"] == "http.response.body":
                        if not started[0]:
                            raise Exception(
                                "Expected the http.responsie.start event to be sent first"
                            )
                        body = event.get("body")
                        if body:
                            if LOGGING:
                                info(body)
                            to_send[0] += body
                    else:
                        raise Exception("Unknown event type")

                await application(scope, receive, send)
                writer.write(to_send[0])
                if should_close[0]:
                    if LOGGING:
                        info("Close the connection")
                    writer.close()
                    break
        # except ConnectionResetError:
        #     # The connection is already closed, nothing to do
        #     if LOGGING:
        #         debug("Connection reset")
        except BadRequest as e:
            error(e)
            response = b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: 11\r\n\r\nBad Request"
            writer.write(response)
            writer.close()
        # https://stackoverflow.com/questions/7160983/catching-all-exceptions-in-python
        except Exception as e:
            error(type(e), e)
            traceback.print_exception(e)
            sys.stdout.flush()
            response = b"HTTP/1.1 500 Error\r\nConnection: close\r\nContent-Length: 5\r\n\r\nError"
            writer.write(response)
            writer.close()
    return handle_connection_run

# https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
async def serve(num, application, p):
    server = await asyncio.start_server(handle_connection(application), **p)
    if sys.implementation.name == 'micropython':
        log(f"Serving worker 1")
    else:
        log(f"Serving worker {num} (pid {os.getpid()})")
    sys.stdout.flush()
    await server.wait_closed()

def run_worker(num, application, p):
    asyncio.run(serve(num, application, p))

def main(application, address, num_workers):
    if sys.implementation.name == 'micropython':
        host, port = address.split(":")
        port = int(port)
        p = dict(host=host, port=port)
        assert num_workers == 1, 'Only one worker allowed in micropython'
    else:
        sock = create_socket(address)
        p = dict(sock=sock)
    if num_workers != 1:
        workers = []
        try:
            import multiprocessing
            # Run all but one in separate processes
            for i in range(num_workers - 1):
                worker = multiprocessing.Process(
                    target=run_worker, args=(i + 2, application, p)
                )
                worker.daemon = True
                worker.start()
                workers.append(worker)
            # Run one worker in this process
            run_worker(1, application, p)
        except KeyboardInterrupt:
            log(f"Shutting down worker processes ...")
            for worker in workers:
                worker.terminate()
            for worker in workers:
                worker.join()
    else:
        try:
            run_worker(1, application, p)
        except KeyboardInterrupt:
            log(f"Shutting down worker processes ...")
        log("Finished.")
