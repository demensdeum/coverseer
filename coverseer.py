import sys
import subprocess
import time
import threading
import json
import logging
from typing import List, Optional
from ollama_call import ollama_call

# Configuration
CHECK_INTERVAL_SECONDS = 30
MAX_OUTPUT_LINES = 100
OLLAMA_MODEL = "gemma3:4b"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProcessMonitor:
    def __init__(self, command: List[str]):
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self.output_buffer: List[str] = []
        self.buffer_lock = threading.Lock()
        self.stop_requested = False

    def _read_output(self):
        """Worker thread to read stdout and stderr from the child process."""
        if not self.process:
            return

        # Read line by line
        for line in self.process.stdout:
            if line:
                line_str = line.strip()
                logger.info(f"[Child]: {line_str}")
                with self.buffer_lock:
                    self.output_buffer.append(line_str)
                    if len(self.output_buffer) > MAX_OUTPUT_LINES:
                        self.output_buffer.pop(0)

    def _check_process(self) -> bool:
        """Consults Ollama to see if the process needs a restart.
        Returns True if restart is needed.
        """
        with self.buffer_lock:
            recent_output = "\n".join(self.output_buffer)

        if not recent_output:
            logger.info("Output buffer is empty, skipping health check.")
            return False

        prompt = (
            "Analyze the following process output and decide if the process is stuck, crashed, "
            "or in an error state that requires a restart. Respond ONLY with a JSON object.\n\n"
            f"Output:\n{recent_output}"
        )

        format_schema = {
            "type": "object",
            "properties": {
                "restart_needed": {"type": "boolean"},
                "reason": {"type": "string"}
            },
            "required": ["restart_needed", "reason"]
        }

        try:
            logger.info("Contacting Ollama for health check...")
            response = ollama_call(
                user_prompt=prompt,
                format=format_schema,
                model=OLLAMA_MODEL
            )
            
            # ollama_call returns the full response object, we need the "response" field
            # which might be a string containing JSON or a dict depending on internal logic
            raw_response = response.get("response", "")
            if isinstance(raw_response, str):
                data = json.loads(raw_response)
            else:
                data = raw_response

            if data.get("restart_needed"):
                logger.warning(f"Ollama requested RESTART. Reason: {data.get('reason')}")
                return True
            else:
                logger.info("Ollama says OK.")
                return False

        except Exception as e:
            logger.error(f"Error during Ollama health check: {e}")
            return False

    def start(self):
        while not self.stop_requested:
            # Handle both list and string inputs for better shell compatibility
            cmd_to_run = self.command if len(self.command) > 1 else self.command[0]
            logger.info(f"Starting process: {cmd_to_run}")
            
            self.process = subprocess.Popen(
                cmd_to_run,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True,    # Fixes the binary/buffering warning and handles decoding automagically
                shell=True    # Helps finding executables and handling quoted string commands on Windows
            )

            # Start thread to capture output
            output_thread = threading.Thread(target=self._read_output, daemon=True)
            output_thread.start()

            while self.process.poll() is None:
                time.sleep(CHECK_INTERVAL_SECONDS)
                
                if self._check_process():
                    logger.warning("Restarting process...")
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                    break # Break inner loop to restart

            return_code = self.process.poll()
            if return_code is not None:
                if return_code == 0:
                    logger.info("Process finished successfully.")
                    self.stop_requested = True
                else:
                    logger.warning(f"Process exited with return code {return_code}. Restarting...")
                    time.sleep(2) # Backoff before restart

def main():
    if len(sys.argv) < 2:
        print("Usage: python coverseer.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1:]
    monitor = ProcessMonitor(command)
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting...")
        if monitor.process:
            monitor.process.terminate()

if __name__ == "__main__":
    main()
