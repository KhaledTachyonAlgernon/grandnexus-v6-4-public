from __future__ import annotations
import logging
import threading
import time
import uuid
import sqlite3
import json  # For serializing/deserializing module configurations
from typing import Dict, Any, Optional, List, Callable, Union, Tuple, Set  # Importer Set
import heapq  # Correctly manage priorities



class NexusCore:
    """
    Central class orchestrating the GrandNexus system.
    Provides a unified access point for module management,
    lifecycle control, and inter-module communication.

    Features:
        - Registration of modules with optional dependencies
        - Topological sorting of dependencies for startup and shutdown
        - Hooks for lifecycle events (pre_start, post_start, pre_stop, post_stop)
        - Priority-based message queue with optional background processing
        - Persistence of module state, dependencies, and configuration using SQLite
        - Extensive logging and error checks
        - Convenience methods to add or list modules, get module status and configuration
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, enable_async_messaging: bool = True, db_file: str = "nexuscore.db"):
        """
        Initializes the NexusCore with an optional configuration.

        Args:
            config (dict, optional):  Global configuration dictionary. Defaults to None.
            enable_async_messaging (bool): If True, use a background thread to process the message queue. Defaults to True.
            db_file (str): Path to the SQLite database file. Defaults to "nexuscore.db".
        """
        self.instance_id: str = str(uuid.uuid4())[:8]
        self.logger: logging.Logger = self._setup_logger()
        self.config: Dict[str, Any] = config or {}
        self.modules: Dict[str, Dict[str, Any]] = {}  # {module_name: {instance, dependencies, status, config}}
        self.running: bool = False
        self.start_time: float = 0.0
        self.stop_event: threading.Event = threading.Event()

        # Hooks for lifecycle customization
        self.pre_start_hooks: List[Callable[['NexusCore'], None]] = []
        self.post_start_hooks: List[Callable[['NexusCore'], None]] = []
        self.pre_stop_hooks: List[Callable[['NexusCore'], None]] = []
        self.post_stop_hooks: List[Callable[['NexusCore'], None]] = []

        # Priority-based Message queue
        self.message_queue: List[Tuple[int, Dict[str, Any]]] = []  # (priority, message)
        self.lock: threading.RLock = threading.RLock()

        self.enable_async_messaging: bool = enable_async_messaging
        self.message_thread: Optional[threading.Thread] = None

        self.db_file: str = db_file
        self._init_db()
        self._load_modules_from_db()

        self.logger.info(f"NexusCore initialized with ID={self.instance_id}, Async Messaging: {enable_async_messaging}")

        # Initialize error recovery manager
        self.error_recovery = ErrorRecoveryManager(self)

        self.logger.info(f"NexusCore initialized with ID={self.instance_id}, Async Messaging: {enable_async_messaging}")


    def _setup_logger(self) -> logging.Logger:
        """Configures and returns a logger for the core."""
        logger = logging.getLogger("NexusCore")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _init_db(self):
        """Initializes the SQLite database."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS modules (
                        name TEXT PRIMARY KEY,
                        status TEXT,
                        configuration TEXT,  -- Store configuration as JSON
                        last_updated REAL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dependencies (
                        module_name TEXT,
                        dependency_name TEXT,
                        FOREIGN KEY (module_name) REFERENCES modules(name) ON DELETE CASCADE,
                        FOREIGN KEY (dependency_name) REFERENCES modules(name) ON DELETE CASCADE,
                        PRIMARY KEY (module_name, dependency_name)
                    )
                """)
                # You could add a 'metadata' table here, similar to nsytz's version.
                conn.commit()
            self.logger.info("Database initialized successfully.")

        except sqlite3.Error as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise  # Re-raise to prevent startup if DB init fails

    def _load_modules_from_db(self):
        """Loads module information from the database."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, status, configuration FROM modules")
                for name, status, configuration in cursor.fetchall():
                    self.modules[name] = {
                        "instance": None,  # Placeholder, will be filled on register
                        "dependencies": [],  # Will be filled below
                        "status": status,
                        "config": json.loads(configuration) if configuration else {}  # Load config
                    }

                cursor.execute("SELECT module_name, dependency_name FROM dependencies")
                for module_name, dependency_name in cursor.fetchall():
                    if module_name in self.modules:
                        self.modules[module_name]["dependencies"].append(dependency_name)
        except sqlite3.Error as e:
            self.logger.error(f"Error loading modules from database: {e}")
            #  Don't re-raise here.  Allow registration, but log the error

    def _persist_module(self, name: str):
        """Persists module information to the database."""
        with self.lock:
            if name not in self.modules:
                return # Nothing to persist.

            module_info = self.modules[name]
            status = module_info["status"]
            config = module_info.get("config", {})  # Get config, default to empty dict
            config_json = json.dumps(config)       # Serialize configuration
            dependencies = module_info["dependencies"]

            try:
                with sqlite3.connect(self.db_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO modules (name, status, configuration, last_updated)
                        VALUES (?, ?, ?, ?)
                    """, (name, status, config_json, time.time()))

                    # Clear existing dependencies
                    cursor.execute("DELETE FROM dependencies WHERE module_name = ?", (name,))
                    # Insert new dependencies
                    for dep in dependencies:
                        cursor.execute("INSERT INTO dependencies (module_name, dependency_name) VALUES (?, ?)", (name, dep))
                    conn.commit()
            except sqlite3.Error as e:
                self.logger.error(f"Error persisting module '{name}' to database: {e}")
                # Consider if you want to re-raise, or handle the error here

    def register_module(self, name: str, module: Any, dependencies: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Registers a module in the system.

        Args:
            name (str): Unique identifier for the module.
            module (Any): Instance of the module to register.
            dependencies (List[str], optional): List of module names this module depends on. Defaults to None.
            config (Dict[str, Any], optional): Initial configuration for the module.
        """
        with self.lock:
            if name in self.modules:
                self.logger.warning(f"Module '{name}' is already registered. Overwriting the existing module entry.")

            # Check dependencies
            if dependencies:
                for dep in dependencies:
                    if dep not in self.modules and dep != name: # Allow self-dependency.
                        self.logger.error(f"Dependency '{dep}' not found for module '{name}'.  Registration may fail.")
                        #  Don't raise an exception here; allow the system to try to continue.

            self.modules[name] = {
                "instance": module,
                "dependencies": dependencies or [],
                "status": "registered",
                "config": config or {}  # Store initial configuration
            }
            self.logger.info(f"Module '{name}' registered successfully with status='registered'.")
            self._persist_module(name)  # Persist after *successful* registration

    def get_module(self, name: str) -> Optional[Any]:
        """Retrieves a module by its name."""
        with self.lock:
            module_info = self.modules.get(name)
            if module_info:
                return module_info["instance"]
            return None

    def get_module_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves the configuration of a module."""
        with self.lock:
            module_info = self.modules.get(name)
            if module_info:
                return module_info.get("config")  # Return config, or None
            return None

    def set_module_config(self, name: str, config: Dict[str, Any]) -> None:
        """
        Sets or updates the configuration for a module.

        Args:
             name (str): The name of the module
             config (Dict[str, Any]):  The configuration dictionary
        """
        with self.lock:
            if name not in self.modules:
                self.logger.error(f"Cannot set configuration: Module '{name}' not found.")
                return

            module_info = self.modules[name]
            module_info["config"] = config

            # Call set_configuration if available.
            instance = module_info['instance']
            if instance and hasattr(instance, 'set_configuration') and callable(getattr(instance, 'set_configuration')):
                try:
                    instance.set_configuration(config)
                    self.logger.info(f"Module '{name}' configuration updated and applied.")
                except Exception as e:
                     self.logger.error(f"Error applying configuration to module '{name}': {e}")
                     #  Don't change the module status here, as the module might still be functional

            self._persist_module(name) # Persist new config
            self.logger.info(f"Module '{name}' configuration updated in registry.")


    def list_modules(self) -> List[str]:
        """Lists all registered modules by name."""
        with self.lock:
            return list(self.modules.keys())

    def start(self) -> bool:
      """
      Starts the NexusCore and all registered modules in the order of their dependencies.

      Returns:
          bool: True if started successfully, False otherwise
      """
      if self.running:
          self.logger.warning("NexusCore is already running.")
          return True

      self.logger.info(f"Starting NexusCore [{self.instance_id}]")

      # Execute pre-start hooks
      pre_hooks_success = self._execute_hooks('pre_start')
      if not pre_hooks_success:
          self.logger.warning("Some pre-start hooks failed, but continuing with startup")

      self.stop_event.clear()
      self.start_time = time.time()
      self.running = True

      # Determine startup order based on dependencies
      try:
          start_order = self._resolve_dependencies()
          self.logger.info(f"Module startup order resolved to: {start_order}")
      except ValueError as e:
          self.logger.error(f"Failed to start NexusCore: {e}")
          self.running = False  # Reset running flag
          return False  # Exit if dependency resolution fails

      # Start each module in the resolved order
      start_success = True
      for module_name in start_order:
          if not self._start_module(module_name):
              start_success = False
              # Continue starting other modules unless configured otherwise
              if self.config.get("fail_fast", False):
                  break

      # Start the background thread for message processing if enabled
      if self.enable_async_messaging:
          self._start_async_message_processing()

      # Execute post-start hooks
      post_hooks_success = self._execute_hooks('post_start')
      if not post_hooks_success:
          self.logger.warning("Some post-start hooks failed")

      if start_success:
          self.logger.info(f"NexusCore [{self.instance_id}] started successfully.")
      else:
          self.logger.warning(f"NexusCore [{self.instance_id}] started with some module failures.")

      return start_success

    def stop(self) -> bool:
      """
      Gracefully stops NexusCore and all modules.

      Returns:
          bool: True if stopped successfully, False otherwise
      """
      if not self.running:
          self.logger.warning("NexusCore is not running.")
          return True

      self.logger.info(f"Stopping NexusCore [{self.instance_id}]")

      # Execute pre-stop hooks
      pre_hooks_success = self._execute_hooks('pre_stop')
      if not pre_hooks_success:
          self.logger.warning("Some pre-stop hooks failed, but continuing with shutdown")

      self.running = False
      self.stop_event.set()

      # Stop the asynchronous message processing thread if running
      if self.message_thread and self.message_thread.is_alive():
          self.logger.info("Waiting for the message processing thread to finish...")
          self.message_thread.join(timeout=5.0)  # Give it some time to exit
          if self.message_thread.is_alive():
              self.logger.warning("Message processing thread did not exit cleanly within 5 seconds.")

      # Determine the order to stop modules (reverse of the startup order)
      stop_success = True
      try:
          stop_order = list(reversed(self._resolve_dependencies()))
          self.logger.info(f"Module shutdown order resolved to: {stop_order}")
      except ValueError as e:
          self.logger.error(f"Error during shutdown dependency resolution: {e}. Forcing shutdown of known modules.")
          stop_order = list(self.modules.keys())  # Attempt to stop all registered, even with bad dependency graph.

      # Stop modules in reverse order
      for module_name in stop_order:
          if not self._stop_module(module_name):
              stop_success = False
              # Continue stopping other modules

      # Execute post-stop hooks
      post_hooks_success = self._execute_hooks('post_stop')
      if not post_hooks_success:
          self.logger.warning("Some post-stop hooks failed")

      uptime = time.time() - self.start_time
      self.logger.info(f"NexusCore [{self.instance_id}] stopped. Total uptime: {uptime:.2f}s")

      return stop_success

      # Arrêter le gestionnaire d'erreurs
      self.error_recovery.shutdown()
      return success

    # Amélioration pour NexusCore._resolve_dependencies()
    def _resolve_dependencies(self) -> List[str]:
        """
        Determines the startup (and shutdown) order of modules based on dependencies.
        Uses topological sorting (Kahn's Algorithm) with improved cycle detection and error handling.

        Returns:
            List[str]: Names of modules in the correct startup order.
        Raises:
            ValueError: If a circular dependency is detected, with detailed information about the cycle.
        """
        with self.lock:
            # Build the dependency graph and track reverse dependencies for cycle detection
            graph = {name: set(info["dependencies"]) for name, info in self.modules.items()}
            reverse_graph = {name: set() for name in self.modules}

            # Populate reverse graph for cycle detection
            for node, deps in graph.items():
                for dep in deps:
                    if dep in reverse_graph:  # Check if dependency is registered
                        reverse_graph[dep].add(node)
                    else:
                        self.logger.warning(f"Module '{node}' depends on unknown module '{dep}'")

            # Kahn's Algorithm with cycle detection
            in_degree = {node: 0 for node in graph}
            for node in graph:
                for dep in graph.get(node, []):
                    if dep in in_degree:  # Check if dependency is registered
                        in_degree[dep] += 1

            # Create priority queue for processing nodes
            queue = [(0, node) for node, degree in in_degree.items() if degree == 0]
            heapq.heapify(queue)
            order = []

            # Process nodes in priority order
            while queue:
                _, node = heapq.heappop(queue)
                order.append(node)

                for neighbor in list(graph.get(node, [])):
                    if neighbor in in_degree:  # Check if neighbor is registered
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0:
                            # Use module priority in heap if available, default to 0
                            priority = self.modules.get(neighbor, {}).get("priority", 0)
                            heapq.heappush(queue, (priority, neighbor))

            # Check for circular dependencies
            if len(order) != len(self.modules):
                # Find and report the cycle
                remaining = set(self.modules.keys()) - set(order)
                cycles = self._find_dependency_cycles(remaining, graph, reverse_graph)
                cycle_str = '; '.join([' -> '.join(cycle) for cycle in cycles])
                raise ValueError(f"Circular dependency detected: {cycle_str}")

            return order

    # New helper method for cycle detection
    def _find_dependency_cycles(self, nodes: Set[str], graph: Dict[str, Set[str]],
                              reverse_graph: Dict[str, Set[str]]) -> List[List[str]]:
        """
        Helper method to find and report cycles in the dependency graph.

        Args:
            nodes: Set of nodes that are part of a cycle
            graph: Forward dependency graph
            reverse_graph: Reverse dependency graph for cycle detection

        Returns:
            List of cycles, where each cycle is a list of module names
        """
        cycles = []
        visited = set()

        def dfs(node, path, visited_in_path):
            if node in visited_in_path:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            visited.add(node)
            visited_in_path.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor in nodes and neighbor not in visited:
                    dfs(neighbor, path, visited_in_path.copy())

            path.pop()
            visited_in_path.remove(node)

        # Try to find cycles starting from each remaining node
        for node in nodes:
            if node not in visited:
                dfs(node, [], set())

        return cycles


    def _start_module(self, name: str) -> bool:
      """
      Starts a specific module by name, calling its start() method if available.

      Args:
          name (str): Name of the module to start.

      Returns:
          bool: True if module started successfully, False otherwise
      """
      with self.lock:
          if name not in self.modules:
              self.logger.error(f"Cannot start '{name}': Module not found.")
              return False

          module_info = self.modules[name]
          if module_info["status"] == "running":
              self.logger.debug(f"Module '{name}' is already running.")
              return True

          instance = module_info["instance"]
          try:
              start_method = getattr(instance, "start", None)
              if callable(start_method):
                  start_method()
                  self.logger.info(f"Module '{name}' started successfully.")
              else:
                  self.logger.debug(f"Module '{name}' has no start() method. Marking as 'running' anyway.")
              module_info["status"] = "running"
              self._persist_module(name)  # Persist new status
              return True
          except Exception as e:
              # Appeler error_recovery
              recovery_result = self.error_recovery.handle_error(name, e, "start")
              if not recovery_result["success"]:
                  self.logger.error(f"Error while starting module '{name}': {e}", exc_info=True)
                  module_info["status"] = "error"
                  module_info.setdefault("error_info", {})
                  module_info["error_info"]["last_error"] = str(e)
                  module_info["error_info"]["last_error_time"] = time.time()
                  self._persist_module(name)  # Persist error status
              return recovery_result["success"]


    def _stop_module(self, name: str) -> bool:
      """
      Stops a specific module by name, calling its stop() method if available.

      Args:
          name (str): Name of the module to stop.

      Returns:
          bool: True if module stopped successfully, False otherwise
      """
      with self.lock:
          if name not in self.modules:
              self.logger.error(f"Cannot stop '{name}': Module not found.")
              return False

          module_info = self.modules[name]
          if module_info["status"] != "running":
              self.logger.debug(f"Module '{name}' is not currently running. Status is '{module_info['status']}'.")
              return True  # Consider it a success if it's already not running

          instance = module_info["instance"]
          try:
              stop_method = getattr(instance, "stop", None)
              if callable(stop_method):
                  stop_method()
                  self.logger.info(f"Module '{name}' stopped successfully.")
              else:
                  self.logger.debug(f"Module '{name}' has no stop() method. Marking as 'stopped'.")
              module_info["status"] = "stopped"
              self._persist_module(name)  # Persist
              return True
          except Exception as e:
              self.logger.error(f"Error while stopping module '{name}': {e}", exc_info=True)
              module_info["status"] = "error"
              module_info.setdefault("error_info", {})
              module_info["error_info"]["last_error"] = str(e)
              module_info["error_info"]["last_error_time"] = time.time()
              self._persist_module(name)  # Persist
              return False

    # Améliorations pour les hooks du cycle de vie

    def add_hook(self, hook_type: str, hook_func: Callable[['NexusCore'], None]) -> bool:
        """
        Adds a hook to the core lifecycle.

        Args:
            hook_type (str): Type of hook ('pre_start', 'post_start', 'pre_stop', 'post_stop').
            hook_func (Callable[['NexusCore'], None]): Function to execute during the hook.

        Returns:
            bool: True if the hook was added successfully, False otherwise.
        """
        valid_hooks = {'pre_start', 'post_start', 'pre_stop', 'post_stop'}

        if hook_type not in valid_hooks:
            self.logger.warning(f"Unknown hook type: {hook_type}. Valid types are: {valid_hooks}")
            return False

        if not callable(hook_func):
            self.logger.warning(f"Hook function must be callable")
            return False

        hook_list = getattr(self, f"{hook_type}_hooks")

        # Avoid duplicate hooks
        if hook_func in hook_list:
            self.logger.debug(f"Hook function already registered for {hook_type}")
            return True

        hook_list.append(hook_func)
        self.logger.debug(f"Added {hook_type} hook: {hook_func.__name__}")
        return True

    def remove_hook(self, hook_type: str, hook_func: Callable[['NexusCore'], None]) -> bool:
        """
        Removes a previously added hook from the core lifecycle.

        Args:
            hook_type (str): Type of hook ('pre_start', 'post_start', 'pre_stop', 'post_stop').
            hook_func (Callable[['NexusCore'], None]): Function to remove.

        Returns:
            bool: True if the hook was removed successfully, False if not found.
        """
        valid_hooks = {'pre_start', 'post_start', 'pre_stop', 'post_stop'}

        if hook_type not in valid_hooks:
            self.logger.warning(f"Unknown hook type: {hook_type}. Valid types are: {valid_hooks}")
            return False

        hook_list = getattr(self, f"{hook_type}_hooks")

        if hook_func not in hook_list:
            self.logger.debug(f"Hook function not found in {hook_type} hooks")
            return False

        hook_list.remove(hook_func)
        self.logger.debug(f"Removed {hook_type} hook: {hook_func.__name__}")
        return True

    def _execute_hooks(self, hook_type: str) -> bool:
        """
        Internal method to execute all hooks of a given type.

        Args:
            hook_type (str): Type of hooks to execute

        Returns:
            bool: True if all hooks executed successfully, False if any hooks failed
        """
        hook_list = getattr(self, f"{hook_type}_hooks")
        all_succeeded = True

        for i, hook in enumerate(hook_list):
            try:
                self.logger.debug(f"Executing {hook_type} hook {i+1}/{len(hook_list)}: {hook.__name__}")
                hook(self)
            except Exception as e:
                all_succeeded = False
                self.logger.error(f"Error in {hook_type} hook {hook.__name__}: {e}", exc_info=True)
                # Continue with other hooks even if one fails

        return all_succeeded

    def send_message(self, source: str, target: str, message_type: str, content: Any, priority: int = 1) -> None:
        """
        Sends a message from one module to another.  Adds the message to the priority queue.

        Args:
            source (str): Source module name.
            target (str): Target module name.
            message_type (str): Type/category of the message.
            content (Any): The message payload.
            priority (int):  Message priority (lower is higher).
        """

        message = {
            "source": source,
            "target": target,
            "type": message_type,
            "content": content,
            "timestamp": time.time()
        }

        with self.lock:
            heapq.heappush(self.message_queue, (priority, message))  # Use heapq
            self.logger.debug(f"Message from '{source}' to '{target}' (type: {message_type}, priority: {priority}) queued.")

        # If asynchronous messaging is disabled, process messages immediately
        if not self.enable_async_messaging:
            self._process_messages()


    def _process_messages(self):
        """
        Process messages from the queue.  This is either called immediately after
        send_message (if async is disabled) or runs in a separate thread (if async is enabled).
        """
        with self.lock:
            while self.message_queue:
                priority, message = heapq.heappop(self.message_queue) # Use heappop
                self._deliver_message(message)



    def _deliver_message(self, message: Dict[str, Any]) -> None:
        """
        Deliver the message directly to the target's handle_message method, if it exists.
        This is used both in synchronous mode or by the background thread in asynchronous mode.

        Args:
            message (dict): The message to be delivered.
        """
        target = message["target"]
        with self.lock:
            if target in self.modules:
                target_module = self.modules[target]["instance"]
                handle_method = getattr(target_module, "handle_message", None)
                if callable(handle_method):
                    try:
                        handle_method(message)
                    except Exception as e:
                        self.logger.error(f"Error processing message by '{target}': {e}")

    def _start_async_message_processing(self) -> None:
        """
        Spawns a background thread that continuously processes messages from the queue
        until the core is stopped.  The thread calls _deliver_message for each message.
        """

        def message_loop():
            self.logger.info("Asynchronous message processing thread started.")
            while self.running and not self.stop_event.is_set():
                self._process_messages()  # Process all available messages
                time.sleep(0.01)  # Avoid busy-waiting if queue is empty, check frequently
            self.logger.info("Asynchronous message processing thread exiting.")

        self.message_thread = threading.Thread(target=message_loop, daemon=True)
        self.message_thread.start()

    def get_status(self) -> Dict[str, Any]:
        """
        Retrieves the current status of NexusCore and its modules,
        including health information from ErrorRecoveryManager.

        Returns:
            Dict[str, Any]: Dictionary containing status information.
        """
        with self.lock:
            if self.running:
                uptime = time.time() - self.start_time
            else:
                uptime = 0

            modules_status = {}
            for name, info in self.modules.items():
                modules_status[name] = {
                    "status": info["status"],
                    "dependencies": info["dependencies"],
                    "config": info.get("config", {})  # Include configuration
                }

                # Add health information from error recovery manager
                if hasattr(self, "error_recovery"):
                    health_info = self.error_recovery.get_module_health_status(name)
                    modules_status[name]["health"] = health_info

                # If the module has a get_status() method, include that info
                instance = info["instance"]
                get_status_method = getattr(instance, "get_status", None)
                if callable(get_status_method):
                    try:
                        module_status = get_status_method()
                        if isinstance(module_status, dict):
                            modules_status[name].update(module_status)
                    except Exception as e:
                        self.logger.error(f"Error retrieving status for '{name}': {e}")

            status = {
                "instance_id": self.instance_id,
                "running": self.running,
                "uptime": uptime,
                "modules": modules_status,
                "queue_size": len(self.message_queue),
                "async_messaging_enabled": self.enable_async_messaging
            }

            # Add recovery enabled flag if error recovery is available
            if hasattr(self, "error_recovery"):
                status["recovery_enabled"] = True

            return status



    def update_module_status(self, module_name: str, new_status: str):
        """Updates the status of a module and persists it."""
        with self.lock:
            if module_name in self.modules:
                self.modules[module_name]['status'] = new_status
                self._persist_module(module_name)
                self.logger.info(f"Module '{module_name}' status updated to '{new_status}'")
            else:
                self.logger.error(f"Cannot update status: Module '{module_name}' not found")


class ErrorRecoveryManager:
    """
    Gestionnaire de récupération d'erreurs pour GrandNexus.

    Cette classe implémente diverses stratégies pour récupérer des erreurs,
    y compris les tentatives automatiques avec backoff exponentiel, la surveillance
    de l'état des modules, et l'isolation des modules problématiques.

    Elle est conçue pour collaborer avec NexusCore sans modifier son paradigme
    d'orchestration fondamental.
    """

    # Niveaux de gravité des erreurs
    SEVERITY_LOW = 1     # Problèmes mineurs, peuvent être ignorés
    SEVERITY_MEDIUM = 2  # Problèmes significatifs, doivent être traités
    SEVERITY_HIGH = 3    # Problèmes critiques, nécessitent une attention immédiate

    # Stratégies de récupération
    STRATEGY_IGNORE = "ignore"           # Journaliser et continuer
    STRATEGY_RETRY = "retry"             # Réessayer l'opération
    STRATEGY_RESTART = "restart"         # Redémarrer le module
    STRATEGY_ISOLATE = "isolate"         # Isoler le module
    STRATEGY_NOTIFY = "notify"           # Notifier les administrateurs

    def __init__(self, core_reference):
        """
        Initialise le gestionnaire de récupération d'erreurs.

        Args:
            core_reference: Référence à l'instance NexusCore (utilisée uniquement pour les callbacks)
        """
        self.core = core_reference
        self.logger = logging.getLogger("ErrorRecoveryManager")

        # Suivi de l'état des modules et des tentatives de récupération
        self.module_health: Dict[str, Dict[str, Any]] = {}
        self.recovery_attempts: Dict[str, Dict[str, Any]] = {}

        # Configuration des stratégies de récupération
        self.max_retry_attempts = 3
        self.max_restart_attempts = 2
        self.backoff_base = 2  # Base pour le backoff exponentiel
        self.health_check_interval = 60  # secondes

        # Démarrer le thread de surveillance de l'état
        self.stop_monitoring = threading.Event()
        self.monitoring_thread = threading.Thread(target=self._health_monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        self.logger.info("ErrorRecoveryManager initialisé")

    def handle_error(self, module_name: str, error: Exception, operation: str,
                    severity: int = SEVERITY_MEDIUM) -> Dict[str, Any]:
        """
        Gère une erreur survenue dans un module.

        Args:
            module_name: Nom du module où l'erreur s'est produite
            error: L'exception qui a été levée
            operation: L'opération qui était en cours (ex: "start", "stop", "message")
            severity: Niveau de gravité de l'erreur

        Returns:
            Dict contenant l'action de récupération prise et le résultat
        """
        self.logger.error(f"Erreur dans le module '{module_name}' pendant {operation}: {error}")

        # Initialiser le suivi de l'état du module si inexistant
        if module_name not in self.module_health:
            self.module_health[module_name] = {
                "error_count": 0,
                "last_error_time": 0,
                "consecutive_errors": 0,
                "status": "healthy"
            }

        # Mettre à jour l'état du module
        health = self.module_health[module_name]
        health["error_count"] += 1
        health["last_error_time"] = time.time()
        health["consecutive_errors"] += 1

        # Déterminer la stratégie de récupération en fonction de la gravité et du contexte
        strategy = self._determine_strategy(module_name, error, operation, severity)

        # Exécuter la stratégie de récupération
        result = self._execute_strategy(module_name, strategy, error, operation)

        # Mettre à jour l'état du module en fonction du résultat de la récupération
        if result.get("success", False):
            health["consecutive_errors"] = 0
            if health["status"] == "degraded":
                health["status"] = "recovering"
        else:
            if health["consecutive_errors"] > 3:
                health["status"] = "degraded"
            if health["consecutive_errors"] > 5:
                health["status"] = "critical"

        return result

    def _determine_strategy(self, module_name: str, error: Exception,
                           operation: str, severity: int) -> str:
        """
        Détermine la stratégie de récupération appropriée en fonction du contexte.

        Args:
            module_name: Nom du module
            error: L'exception qui s'est produite
            operation: L'opération en cours
            severity: Niveau de gravité de l'erreur

        Returns:
            La stratégie de récupération sélectionnée
        """
        # Obtenir les informations sur l'état du module
        health = self.module_health.get(module_name, {})
        consecutive_errors = health.get("consecutive_errors", 0)

        # Obtenir les informations sur les tentatives de récupération
        if module_name not in self.recovery_attempts:
            self.recovery_attempts[module_name] = {
                "retry_count": 0,
                "restart_count": 0,
                "last_attempt_time": 0
            }
        attempts = self.recovery_attempts[module_name]

        # Logique pour déterminer la stratégie
        if severity == self.SEVERITY_LOW:
            return self.STRATEGY_IGNORE

        elif severity == self.SEVERITY_MEDIUM:
            # Pour les opérations start/stop, essayer de redémarrer
            if operation in ["start", "stop"]:
                if attempts["restart_count"] < self.max_restart_attempts:
                    return self.STRATEGY_RESTART
                else:
                    return self.STRATEGY_ISOLATE

            # Pour le traitement des messages, essayer de réessayer
            elif operation == "message":
                if attempts["retry_count"] < self.max_retry_attempts:
                    return self.STRATEGY_RETRY
                else:
                    return self.STRATEGY_IGNORE

            # Par défaut pour une gravité moyenne
            return self.STRATEGY_RETRY

        elif severity == self.SEVERITY_HIGH:
            # Pour les erreurs critiques, essayer de redémarrer une fois puis isoler
            if attempts["restart_count"] < 1:
                return self.STRATEGY_RESTART
            else:
                return self.STRATEGY_ISOLATE

        # Stratégie par défaut
        return self.STRATEGY_RETRY

    def _execute_strategy(self, module_name: str, strategy: str,
                         error: Exception, operation: str) -> Dict[str, Any]:
        """
        Exécute la stratégie de récupération sélectionnée.

        Args:
            module_name: Nom du module
            strategy: La stratégie de récupération à exécuter
            error: L'exception qui s'est produite
            operation: L'opération en cours

        Returns:
            Dict contenant le résultat de l'action de récupération
        """
        result = {
            "module": module_name,
            "strategy": strategy,
            "operation": operation,
            "success": False,
            "message": ""
        }

        attempts = self.recovery_attempts.get(module_name, {
            "retry_count": 0,
            "restart_count": 0,
            "last_attempt_time": 0
        })

        # Calculer le temps de backoff si nécessaire
        current_time = time.time()
        time_since_last_attempt = current_time - attempts.get("last_attempt_time", 0)

        if strategy == self.STRATEGY_IGNORE:
            result["success"] = True
            result["message"] = "Erreur journalisée et ignorée"

        elif strategy == self.STRATEGY_RETRY:
            # Mettre à jour le compteur de tentatives
            attempts["retry_count"] += 1
            attempts["last_attempt_time"] = current_time

            # Calculer le temps de backoff
            backoff_time = self._calculate_backoff(attempts["retry_count"])

            # Si nous devons attendre, le faire
            if time_since_last_attempt < backoff_time:
                time.sleep(backoff_time - time_since_last_attempt)

            # Réessayer l'opération via un callback à NexusCore
            try:
                # Utiliser les callbacks pour maintenir la séparation des responsabilités
                if operation == "start":
                    success = self._callback_start_module(module_name)
                    if success:
                        result["success"] = True
                        result["message"] = f"Module '{module_name}' démarré avec succès après nouvelle tentative"
                elif operation == "stop":
                    success = self._callback_stop_module(module_name)
                    if success:
                        result["success"] = True
                        result["message"] = f"Module '{module_name}' arrêté avec succès après nouvelle tentative"
                elif operation == "message":
                    # Nous ne pouvons pas réessayer la livraison de message directement ici
                    result["success"] = False
                    result["message"] = "Nouvelle tentative de message non implémentée dans ce contexte"
            except Exception as e:
                result["success"] = False
                result["message"] = f"Nouvelle tentative échouée: {str(e)}"

        elif strategy == self.STRATEGY_RESTART:
            # Mettre à jour le compteur de redémarrages
            attempts["restart_count"] += 1
            attempts["last_attempt_time"] = current_time

            # Calculer le temps de backoff
            backoff_time = self._calculate_backoff(attempts["restart_count"])

            # Si nous devons attendre, le faire
            if time_since_last_attempt < backoff_time:
                time.sleep(backoff_time - time_since_last_attempt)

            # Essayer d'arrêter puis de démarrer le module via des callbacks
            try:
                # D'abord essayer d'arrêter s'il est en cours d'exécution
                module_status = self._callback_get_module_status(module_name)
                if module_status == "running":
                    self._callback_stop_module(module_name)

                # Puis essayer de le démarrer
                success = self._callback_start_module(module_name)
                if success:
                    result["success"] = True
                    result["message"] = f"Module '{module_name}' redémarré avec succès"
                else:
                    result["success"] = False
                    result["message"] = f"Échec du redémarrage du module '{module_name}'"
            except Exception as e:
                result["success"] = False
                result["message"] = f"Redémarrage échoué: {str(e)}"

        elif strategy == self.STRATEGY_ISOLATE:
            try:
                # Marquer le module comme isolé via un callback
                success = self._callback_update_module_status(module_name, "isolated")
                if success:
                    # Journaliser l'isolation
                    self.logger.warning(f"Module '{module_name}' a été isolé en raison d'erreurs persistantes")

                    result["success"] = True
                    result["message"] = f"Module '{module_name}' a été isolé"
                else:
                    result["success"] = False
                    result["message"] = f"Impossible d'isoler: Module '{module_name}' non trouvé"
            except Exception as e:
                result["success"] = False
                result["message"] = f"Isolation échouée: {str(e)}"

        elif strategy == self.STRATEGY_NOTIFY:
            # Ceci s'intégrerait généralement à un système de notification externe
            # Pour l'instant, nous le journalisons simplement de manière visible
            self.logger.critical(f"ERREUR CRITIQUE dans le module '{module_name}': {error}")
            result["success"] = True
            result["message"] = "Notification d'erreur journalisée"

        # Mettre à jour les tentatives de récupération
        self.recovery_attempts[module_name] = attempts

        return result

    def _calculate_backoff(self, attempt_count: int) -> float:
        """
        Calcule le temps de backoff exponentiel basé sur le nombre de tentatives.

        Args:
            attempt_count: Nombre de tentatives jusqu'à présent

        Returns:
            Temps de backoff en secondes
        """
        # Backoff exponentiel avec jitter
        backoff = (self.backoff_base ** attempt_count) * (0.5 + 0.5 * (uuid.uuid4().int % 100) / 100)
        return min(backoff, 60)  # Plafonner à 60 secondes

    def _health_monitoring_loop(self):
        """
        Thread d'arrière-plan qui vérifie périodiquement l'état des modules.
        """
        self.logger.info("Thread de surveillance de l'état démarré")

        while not self.stop_monitoring.is_set():
            try:
                self._check_module_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Erreur dans la surveillance de l'état: {e}")
                time.sleep(5)  # Court sommeil en cas d'erreur

        self.logger.info("Thread de surveillance de l'état arrêté")

    def _check_module_health(self):
        """
        Vérifie l'état de tous les modules et tente une récupération si nécessaire.
        """
        # Obtenir la liste des modules et leur état via un callback
        modules_info = self._callback_get_all_modules_info()

        for module_name, module_info in modules_info.items():
            # Ignorer les modules qui ne sont pas en cours d'exécution
            if module_info.get("status") != "running":
                continue

            # Vérifier si le module a une méthode health_check
            has_health_check = self._callback_has_health_check(module_name)

            if has_health_check:
                try:
                    # Appeler la méthode health_check du module via un callback
                    health_status = self._callback_check_module_health(module_name)

                    # Si la vérification de l'état échoue, tenter une récupération
                    if not health_status.get("healthy", True):
                        self.logger.warning(f"Vérification de l'état échouée pour le module '{module_name}': {health_status.get('message', 'Aucun détail')}")

                        # Créer une erreur synthétique pour la récupération
                        error = Exception(f"Vérification de l'état échouée: {health_status.get('message', 'Aucun détail')}")
                        self.handle_error(module_name, error, "health_check", self.SEVERITY_MEDIUM)
                except Exception as e:
                    self.logger.error(f"Erreur pendant la vérification de l'état du module '{module_name}': {e}")

    def reset_recovery_attempts(self, module_name: str):
        """
        Réinitialise les tentatives de récupération pour un module.

        Args:
            module_name: Nom du module
        """
        if module_name in self.recovery_attempts:
            self.recovery_attempts[module_name] = {
                "retry_count": 0,
                "restart_count": 0,
                "last_attempt_time": 0
            }
            self.logger.info(f"Tentatives de récupération réinitialisées pour le module '{module_name}'")

    def get_module_health_status(self, module_name: str = None) -> Dict[str, Any]:
        """
        Obtient l'état de santé d'un module spécifique ou de tous les modules.

        Args:
            module_name: Nom du module, ou None pour tous les modules

        Returns:
            Dict contenant les informations sur l'état de santé
        """
        if module_name:
            return self.module_health.get(module_name, {
                "error_count": 0,
                "last_error_time": 0,
                "consecutive_errors": 0,
                "status": "unknown"
            })
        else:
            return self.module_health

    def shutdown(self):
        """
        Arrête le gestionnaire de récupération d'erreurs.
        """
        self.stop_monitoring.set()
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        self.logger.info("Arrêt d'ErrorRecoveryManager terminé")

    # Méthodes de callback pour maintenir la séparation des responsabilités
    # Ces méthodes appellent NexusCore sans modifier son paradigme d'orchestration

    def _callback_start_module(self, module_name: str) -> bool:
        """
        Callback pour démarrer un module via NexusCore.

        Args:
            module_name: Nom du module à démarrer

        Returns:
            bool: True si le démarrage a réussi, False sinon
        """
        try:
            # Appeler la méthode _start_module de NexusCore
            # Cette approche maintient la séparation des responsabilités
            self.core._start_module(module_name)
            return True
        except Exception as e:
            self.logger.error(f"Callback de démarrage échoué pour '{module_name}': {e}")
            return False

    def _callback_stop_module(self, module_name: str) -> bool:
        """
        Callback pour arrêter un module via NexusCore.

        Args:
            module_name: Nom du module à arrêter

        Returns:
            bool: True si l'arrêt a réussi, False sinon
        """
        try:
            # Appeler la méthode _stop_module de NexusCore
            self.core._stop_module(module_name)
            return True
        except Exception as e:
            self.logger.error(f"Callback d'arrêt échoué pour '{module_name}': {e}")
            return False

    def _callback_get_module_status(self, module_name: str) -> str:
        """
        Callback pour obtenir l'état d'un module via NexusCore.

        Args:
            module_name: Nom du module

        Returns:
            str: État du module
        """
        try:
            # Accéder à l'état du module via NexusCore
            with self.core.lock:
                if module_name in self.core.modules:
                    return self.core.modules[module_name]["status"]
                return "unknown"
        except Exception as e:
            self.logger.error(f"Callback d'obtention d'état échoué pour '{module_name}': {e}")
            return "unknown"

    def _callback_update_module_status(self, module_name: str, status: str) -> bool:
        """
        Callback pour mettre à jour l'état d'un module via NexusCore.

        Args:
            module_name: Nom du module
            status: Nouvel état

        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Utiliser la méthode update_module_status de NexusCore si elle existe
            if hasattr(self.core, "update_module_status") and callable(getattr(self.core, "update_module_status")):
                self.core.update_module_status(module_name, status)
                return True

            # Sinon, mettre à jour directement (moins idéal)
            with self.core.lock:
                if module_name in self.core.modules:
                    self.core.modules[module_name]["status"] = status
                    self.core._persist_module(module_name)
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Callback de mise à jour d'état échoué pour '{module_name}': {e}")
            return False

    def _callback_get_all_modules_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Callback pour obtenir les informations sur tous les modules via NexusCore.

        Returns:
            Dict: Informations sur tous les modules
        """
        try:
            # Accéder aux informations sur les modules via NexusCore
            with self.core.lock:
                return {name: info.copy() for name, info in self.core.modules.items()}
        except Exception as e:
            self.logger.error(f"Callback d'obtention des informations sur les modules échoué: {e}")
            return {}

    def _callback_has_health_check(self, module_name: str) -> bool:
        """
        Callback pour vérifier si un module a une méthode health_check.

        Args:
            module_name: Nom du module

        Returns:
            bool: True si le module a une méthode health_check, False sinon
        """
        try:
            # Vérifier si le module a une méthode health_check
            with self.core.lock:
                if module_name in self.core.modules:
                    instance = self.core.modules[module_name]["instance"]
                    return hasattr(instance, "health_check") and callable(getattr(instance, "health_check"))
                return False
        except Exception as e:
            self.logger.error(f"Callback de vérification de health_check échoué pour '{module_name}': {e}")
            return False

    def _callback_check_module_health(self, module_name: str) -> Dict[str, Any]:
        """
        Callback pour vérifier l'état de santé d'un module.

        Args:
            module_name: Nom du module

        Returns:
            Dict: Résultat de la vérification de l'état de santé
        """
        try:
            # Appeler la méthode health_check du module
            with self.core.lock:
                if module_name in self.core.modules:
                    instance = self.core.modules[module_name]["instance"]
                    health_check = getattr(instance, "health_check", None)
                    if callable(health_check):
                        return health_check()
                return {"healthy": True}
        except Exception as e:
            self.logger.error(f"Callback de vérification de l'état de santé échoué pour '{module_name}': {e}")
            return {"healthy": False, "message": f"Erreur lors de la vérification: {str(e)}"}


class ErrorRecoveryExtension:
    """
    Extension pour NexusCore qui ajoute des capacités de récupération d'erreurs
    sans modifier le paradigme d'orchestration fondamental.

    Cette classe est conçue pour être utilisée comme un mixin ou une extension
    de NexusCore, en ajoutant des points d'intégration minimaux pour la gestion
    d'erreurs.
    """

    def initialize_error_recovery(self):
        """
        Initialise le gestionnaire de récupération d'erreurs.
        Cette méthode doit être appelée après l'initialisation de NexusCore.
        """
        self.error_recovery = ErrorRecoveryManager(self)
        self.logger.info("Gestionnaire de récupération d'erreurs initialisé")

    def _start_module_with_recovery(self, name: str) -> None:
        """
        Version améliorée de _start_module avec récupération d'erreurs.

        Args:
            name (str): Nom du module à démarrer.
        """
        with self.lock:
            if name not in self.modules:
                self.logger.error(f"Impossible de démarrer '{name}': Module non trouvé.")
                return

            module_info = self.modules[name]
            if module_info["status"] == "running":
                self.logger.debug(f"Module '{name}' est déjà en cours d'exécution.")
                return

            # Ignorer les modules isolés
            if module_info["status"] == "isolated":
                self.logger.warning(f"Module '{name}' est isolé en raison d'erreurs précédentes. Démarrage ignoré.")
                return

            instance = module_info["instance"]
            try:
                start_method = getattr(instance, "start", None)
                if callable(start_method):
                    start_method()
                    self.logger.info(f"Module '{name}' démarré avec succès.")
                else:
                    self.logger.debug(f"Module '{name}' n'a pas de méthode start(). Marqué comme 'running' quand même.")
                module_info["status"] = "running"
                self._persist_module(name)  # Persister le nouvel état

                # Réinitialiser les tentatives de récupération en cas de démarrage réussi
                self.error_recovery.reset_recovery_attempts(name)

            except Exception as e:
                # Utiliser le gestionnaire de récupération d'erreurs
                recovery_result = self.error_recovery.handle_error(name, e, "start")

                if not recovery_result["success"]:
                    self.logger.error(f"Erreur lors du démarrage du module '{name}': {e}")
                    module_info["status"] = "error"
                    self._persist_module(name)  # Persister l'état d'erreur

    def _stop_module_with_recovery(self, name: str) -> None:
        """
        Version améliorée de _stop_module avec récupération d'erreurs.

        Args:
            name (str): Nom du module à arrêter.
        """
        with self.lock:
            if name not in self.modules:
                self.logger.error(f"Impossible d'arrêter '{name}': Module non trouvé.")
                return

            module_info = self.modules[name]
            if module_info["status"] != "running":
                self.logger.debug(f"Module '{name}' n'est pas en cours d'exécution. État actuel: '{module_info['status']}'.")
                return

            instance = module_info["instance"]
            try:
                stop_method = getattr(instance, "stop", None)
                if callable(stop_method):
                    stop_method()
                    self.logger.info(f"Module '{name}' arrêté avec succès.")
                else:
                    self.logger.debug(f"Module '{name}' n'a pas de méthode stop(). Marqué comme 'stopped' quand même.")
                module_info["status"] = "stopped"
                self._persist_module(name)  # Persister

                # Réinitialiser les tentatives de récupération en cas d'arrêt réussi
                self.error_recovery.reset_recovery_attempts(name)

            except Exception as e:
                # Utiliser le gestionnaire de récupération d'erreurs
                recovery_result = self.error_recovery.handle_error(name, e, "stop")

                if not recovery_result["success"]:
                    self.logger.error(f"Erreur lors de l'arrêt du module '{name}': {e}")
                    module_info["status"] = "error"
                    self._persist_module(name)  # Persister

    def _deliver_message_with_recovery(self, message: Dict[str, Any]) -> None:
        """
        Version améliorée de _deliver_message avec récupération d'erreurs.

        Args:
            message (dict): Le message à livrer.
        """
        target = message["target"]
        with self.lock:
            if target in self.modules:
                module_info = self.modules[target]

                # Ignorer la livraison de messages aux modules isolés
                if module_info["status"] == "isolated":
                    self.logger.warning(f"Livraison de message ignorée: Module '{target}' est isolé.")
                    return

                target_module = module_info["instance"]
                handle_method = getattr(target_module, "handle_message", None)
                if callable(handle_method):
                    try:
                        handle_method(message)
                    except Exception as e:
                        # Utiliser le gestionnaire de récupération d'erreurs
                        recovery_result = self.error_recovery.handle_error(target, e, "message")

                        if not recovery_result["success"]:
                            self.logger.error(f"Erreur lors du traitement du message par '{target}': {e}")

    def reset_module(self, name: str) -> bool:
        """
        Réinitialise un module qui est en état d'erreur ou isolé, permettant de le démarrer à nouveau.

        Args:
            name (str): Nom du module à réinitialiser

        Returns:
            bool: True si la réinitialisation a réussi, False sinon
        """
        with self.lock:
            if name not in self.modules:
                self.logger.error(f"Impossible de réinitialiser '{name}': Module non trouvé.")
                return False

            module_info = self.modules[name]
            current_status = module_info["status"]

            if current_status in ["error", "isolated"]:
                # Réinitialiser l'état du module
                module_info["status"] = "registered"
                self._persist_module(name)

                # Réinitialiser les tentatives de récupération
                self.error_recovery.reset_recovery_attempts(name)

                self.logger.info(f"Module '{name}' a été réinitialisé de '{current_status}' à 'registered'")
                return True
            else:
                self.logger.warning(f"Module '{name}' est en état '{current_status}', pas 'error' ou 'isolated'. Aucune réinitialisation nécessaire.")
                return False

    def get_enhanced_status(self) -> Dict[str, Any]:
        """
        Version améliorée de get_status qui inclut les informations de santé.

        Returns:
            Dict[str, Any]: Dictionnaire contenant les informations d'état.
        """
        # Appeler d'abord la méthode get_status originale
        status = self.get_status()

        # Ajouter les informations de santé pour chaque module
        for name in status["modules"]:
            health_info = self.error_recovery.get_module_health_status(name)
            status["modules"][name]["health"] = health_info

        # Ajouter des informations sur la récupération d'erreurs
        status["recovery_enabled"] = True

        return status

    def shutdown_with_recovery(self) -> None:
        """
        Version améliorée de stop qui arrête également le gestionnaire de récupération d'erreurs.
        """
        # Arrêter d'abord NexusCore normalement
        self.stop()

        # Puis arrêter le gestionnaire de récupération d'erreurs
        if hasattr(self, "error_recovery"):
            self.error_recovery.shutdown()


class ModuleRegistry:
    """
    Advanced registry for GrandNexus modules.

    The ModuleRegistry is responsible for:
        - Keeping a centralized record of modules (by name).
        - Storing module dependencies (which other modules a given module depends on).
        - Storing dependents (which modules depend on a given module).
        - Tracking module metadata, including lifecycle states, timestamps, version, etc.
        - Managing the registration and unregistration process, ensuring no orphan dependencies.
        - Optionally synchronizing module info with NexusCore (ex: register_module calls).
        - Providing a method to discover and automatically register modules from a Python package.

    This registry can be seen as a companion to NexusCore, focusing on structural and
    informational aspects, while NexusCore handles the operational lifecycle (start/stop).
    """

    VALID_STATES: Set[str] = {
        "REGISTERED",  # Initially registered but not yet started
        "STARTING",    # In the process of starting
        "RUNNING",     # Successfully started and operational
        "STOPPING",    # In the process of stopping
        "STOPPED",     # Successfully stopped
        "ERROR"        # Error state (start, stop, or runtime error)
    }

    def __init__(self, core: Any):
        """
        Initialize the ModuleRegistry.

        Args:
            core: A reference to the NexusCore instance (or similar) that orchestrates
                  the system's lifecycle. This registry can delegate calls to that
                  instance, such as 'register_module', 'update_module_status', etc.
        """
        self.logger: logging.Logger = logging.getLogger("ModuleRegistry")
        self.core = core

        # The following dicts store key info about modules:
        #   self.modules       : { module_name: module_instance }
        #   self.dependencies  : { module_name: [dependencies...] }
        #   self.dependents    : { module_name: set(modules_that_depend_on_it) }
        #   self.metadata      : { module_name: { arbitrary_metadata... } }

        self.modules: Dict[str, Any] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.dependents: Dict[str, Set[str]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

        # Lock to ensure thread safety
        self.lock: threading.RLock = threading.RLock()

        self.logger.info("ModuleRegistry initialized successfully.")

    def register(
        self,
        name: str,
        module_instance: Any,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sync_with_core: bool = True,
        auto_verify: bool = True
    ) -> bool:
        """
        Registers a module along with its dependencies and any custom metadata.

        By default, this method also registers the module with the NexusCore (sync_with_core=True).

        Args:
            name (str):
                The unique identifier for the module. Typically a short string or camelCase name.
            module_instance (Any):
                The Python object (class instance) representing the module. Should have
                at least a 'start()' or 'handle_message()' method to be recognized.
            dependencies (List[str], optional):
                Names of other modules upon which this module depends. If any of those
                modules are not yet registered, a warning is logged. Defaults to None.
            metadata (Dict[str, Any], optional):
                Additional information about the module (version, config, author, etc.).
                This dictionary is stored internally; it may also be partially sent to
                the NexusCore if relevant. Defaults to None.
            sync_with_core (bool):
                If True, automatically invokes 'core.register_module' to keep the
                NexusCore's records aligned. If False, no call is made. Defaults to True.
            auto_verify (bool):
                If True, automatically calls _verify_module_interface to check for
                required methods. Set to False to skip verification. Defaults to True.

        Returns:
            bool: True if registration was successful, False otherwise.

        Raises:
            ValueError:
                If the module fails interface verification (no start() or handle_message()).
        """
        deps = dependencies or []
        meta = metadata or {}

        try:
            with self.lock:
                # If this module is already registered, remove its old dependency links
                if name in self.modules:
                    self.logger.warning(f"Module '{name}' was already registered. Overwriting old entry.")
                    self._remove_dependency_links(name)

                # Validate minimal interface
                if auto_verify:
                    self._verify_module_interface(name, module_instance)

                # Check if dependencies exist in the registry
                for dep in deps:
                    if dep not in self.modules and dep != name:
                        # We do not forcibly raise an error, but we do log it
                        self.logger.warning(f"Dependency '{dep}' for module '{name}' is not yet registered. "
                                            "This may cause startup order issues.")

                # Store the module and its dependencies
                self.modules[name] = module_instance
                self.dependencies[name] = deps.copy()  # store a shallow copy
                self.metadata.setdefault(name, {})
                self.metadata[name].update(meta)       # merge new metadata
                # Set up bidirectional links
                for dep in deps:
                    self.dependents.setdefault(dep, set()).add(name)
                if name not in self.dependents:
                    self.dependents[name] = set()

                # Mark the module's initial state
                self._set_module_state(name, "REGISTERED")

                # Optionally inform the NexusCore
                if sync_with_core and hasattr(self.core, "register_module") and callable(self.core.register_module):
                    # If there's a 'config' key in the metadata, pass it as config param
                    if 'config' in meta:
                        self.core.register_module(name, module_instance, deps, meta['config'])
                    else:
                        self.core.register_module(name, module_instance, deps)

                self.logger.info(f"Module '{name}' registered with dependencies={deps}.")
                return True

        except Exception as e:
            self.logger.error(f"Failed to register module '{name}': {e}", exc_info=True)
            return False

    def unregister(self, name: str) -> bool:
        """
        Unregister a module from the registry, removing any references to it.

        This method checks if any other modules still depend on the one being removed.
        If so, it raises ValueError to prevent accidentally removing a module that is
        still in use.

        Args:
            name (str): The name of the module to unregister.

        Returns:
            bool: True if the unregistration succeeded, False if it could not be done
                  (e.g., module wasn't found).

        Raises:
            ValueError:
                If other modules still depend on the one being removed.
        """
        with self.lock:
            if name not in self.modules:
                self.logger.warning(f"Cannot unregister '{name}': module not found in registry.")
                return False

            # If something depends on this module, we can't remove it
            if name in self.dependents and self.dependents[name]:
                blocking_deps = ", ".join(sorted(self.dependents[name]))
                raise ValueError(
                    f"Cannot unregister module '{name}': the following modules depend on it: {blocking_deps}"
                )

            # Remove references
            self._remove_dependency_links(name)
            del self.modules[name]
            del self.dependencies[name]
            if name in self.dependents:
                del self.dependents[name]
            if name in self.metadata:
                del self.metadata[name]

            # Optionally, one could also call `self.core.unregister_module` if that were desired,
            # but the code from Gemini doesn't do that by default.

            self.logger.info(f"Module '{name}' successfully unregistered.")
            return True

    def get(self, name: str) -> Optional[Any]:
        """
        Retrieve the module instance by name.

        Args:
            name (str): The name of the module to retrieve.

        Returns:
            Optional[Any]: The module instance, or None if it doesn't exist.
        """
        with self.lock:
            return self.modules.get(name)

    def get_all_modules(self) -> Dict[str, Any]:
        """
        Return a dictionary of all registered modules.

        Returns:
            Dict[str, Any]: Copy of the internal registry map (name -> module_instance).
        """
        with self.lock:
            return dict(self.modules)

    def list_module_names(self) -> List[str]:
        """
        Get a list of all module names currently in the registry.

        Returns:
            List[str]: Sorted list of module names.
        """
        with self.lock:
            return sorted(self.modules.keys())

    def get_dependencies(self, name: str) -> List[str]:
        """
        Return the list of modules that the specified module depends on.

        Args:
            name (str): The module whose dependencies we want to retrieve.

        Returns:
            List[str]: Names of the modules that 'name' depends on.

        Raises:
            KeyError: If 'name' is not in the registry.
        """
        with self.lock:
            if name not in self.modules:
                raise KeyError(f"Module '{name}' not found in the registry.")
            return list(self.dependencies[name])

    def get_dependents(self, name: str) -> List[str]:
        """
        Return the list of modules that depend on the specified module.

        Args:
            name (str): The module name for which we want to retrieve dependents.

        Returns:
            List[str]: Names of the modules that depend on 'name'.

        Raises:
            KeyError: If 'name' is not in the registry.
        """
        with self.lock:
            if name not in self.modules:
                raise KeyError(f"Module '{name}' not found in the registry.")
            return sorted(self.dependents.get(name, set()))

    def get_module_metadata(self, name: str) -> Dict[str, Any]:
        """
        Retrieve the metadata dictionary for a given module.

        Args:
            name (str): Name of the module.

        Returns:
            Dict[str, Any]: A (copied) dictionary of the metadata for that module,
                            or an empty dict if none is stored.

        Raises:
            KeyError: If the module is not in the registry.
        """
        with self.lock:
            if name not in self.modules:
                raise KeyError(f"Module '{name}' not found in the registry.")
            meta = self.metadata.get(name, {})
            return dict(meta)  # return a shallow copy

    def set_module_metadata(self, name: str, new_meta: Dict[str, Any]) -> None:
        """
        Set or update the metadata for a given module.

        This merges the existing metadata with 'new_meta', overwriting any
        keys that appear in both.

        Args:
            name (str): The module name to update.
            new_meta (Dict[str, Any]): The new metadata to store.

        Raises:
            KeyError: If the module is not in the registry.
        """
        with self.lock:
            if name not in self.modules:
                raise KeyError(f"Module '{name}' not found in the registry.")
            self.metadata.setdefault(name, {})
            self.metadata[name].update(new_meta)
            self.logger.debug(f"Module '{name}' metadata updated with {new_meta}.")

    def get_module_state(self, name: str) -> str:
        """
        Get the current lifecycle state of a module.

        Args:
            name (str): Name of the module.

        Returns:
            str: The module's current state (REGISTERED, RUNNING, etc.), or "UNKNOWN"
                 if no state is recorded.

        Raises:
            KeyError: If 'name' is not registered.
        """
        with self.lock:
            if name not in self.modules:
                raise KeyError(f"Module '{name}' not found in the registry.")
            return self.metadata.get(name, {}).get("state", "UNKNOWN")

    def set_module_state(self, name: str, state: str, error_reason: Optional[str] = None) -> None:
        """
        Public method to forcibly set a module's state. Typically, internal calls use
        the protected _set_module_state, but you may invoke this method if you need
        to set or override the state externally.

        Args:
            name (str): The module name whose state is changing.
            state (str): The new state (must be in VALID_STATES).
            error_reason (str, optional): Explanation if we are transitioning to ERROR.

        Raises:
            KeyError: If the module is not in the registry.
            ValueError: If the provided state is invalid.
        """
        with self.lock:
            if name not in self.modules:
                raise KeyError(f"Module '{name}' not found in the registry.")
            self._set_module_state(name, state, error_reason=error_reason)

    def resolve_dependency_order(self) -> List[str]:
        """
        Determine a valid startup (or shutdown) order based on module dependencies,
        typically by delegating to the NexusCore's method, if implemented.

        Returns:
            List[str]: A list of module names in an order that respects dependencies.

        Raises:
            ValueError: If circular dependencies are detected or if the resolution fails.
        """
        if hasattr(self.core, "_resolve_dependencies") and callable(self.core._resolve_dependencies):
            self.logger.debug("Resolving dependency order by delegating to NexusCore.")
            return self.core._resolve_dependencies()
        else:
            # If for any reason we cannot delegate to NexusCore, we can do a local topological sort
            self.logger.debug("NexusCore has no _resolve_dependencies method. Performing local topological sort.")
            return self._local_topo_sort()

    def get_module_dependencies(self, name: str, recursive: bool = False, max_depth: int = 10) -> List[str]:
        """
        Get the dependencies of a module, with option for recursive dependency resolution.

        Args:
            name (str): Module name to get dependencies for
            recursive (bool): If True, include all indirect dependencies
            max_depth (int): Maximum recursion depth for recursive dependencies

        Returns:
            List[str]: List of module names that this module depends on

        Raises:
            KeyError: If module name not found
        """
        with self.lock:
            if name not in self.modules:
                raise KeyError(f"Module '{name}' not found in the registry")

            # Direct dependencies
            direct_deps = list(self.dependencies[name])

            # If not recursive, return direct dependencies
            if not recursive:
                return direct_deps

            # Recursive dependency resolution
            all_deps = set(direct_deps)
            to_process = deque([(dep, 1) for dep in direct_deps])  # (dep, depth)

            while to_process:
                dep, depth = to_process.popleft()

                # Stop if we reach max depth
                if depth >= max_depth:
                    continue

                if dep in self.dependencies:
                    for indirect_dep in self.dependencies[dep]:
                        if indirect_dep not in all_deps:
                            all_deps.add(indirect_dep)
                            to_process.append((indirect_dep, depth + 1))

            return list(all_deps)

    def get_module_dependents(self, name: str, recursive: bool = False, max_depth: int = 10) -> List[str]:
        """
        Get modules that depend on the specified module, with option for recursive resolution.

        Args:
            name (str): Module name to get dependents for
            recursive (bool): If True, include all indirect dependents
            max_depth (int): Maximum recursion depth for recursive dependents

        Returns:
            List[str]: List of module names that depend on this module

        Raises:
            KeyError: If module name not found
        """
        with self.lock:
            if name not in self.modules:
                raise KeyError(f"Module '{name}' not found in the registry")

            # Direct dependents
            direct_deps = list(self.dependents.get(name, set()))

            # If not recursive, return direct dependents
            if not recursive:
                return direct_deps

            # Recursive dependent resolution
            all_deps = set(direct_deps)
            to_process = deque([(dep, 1) for dep in direct_deps])  # (dep, depth)

            while to_process:
                dep, depth = to_process.popleft()

                # Stop if we reach max depth
                if depth >= max_depth:
                    continue

                if dep in self.dependents:
                    for indirect_dep in self.dependents[dep]:
                        if indirect_dep not in all_deps:
                            all_deps.add(indirect_dep)
                            to_process.append((indirect_dep, depth + 1))

            return list(all_deps)

    def check_dependency_cycles(self) -> List[List[str]]:
        """
        Check for dependency cycles in the registry.

        Returns:
            List[List[str]]: List of cycles found, where each cycle is a list of module names
            forming a circular dependency chain. Empty list if no cycles found.
        """
        with self.lock:
            # Convert dependencies to a directed graph
            graph = {name: set(deps) for name, deps in self.dependencies.items()}

            # Build reverse graph
            reverse_graph = {name: set() for name in self.modules}
            for node, deps in graph.items():
                for dep in deps:
                    if dep in reverse_graph:
                        reverse_graph[dep].add(node)

            # Try to do a topological sort
            in_degree = {node: 0 for node in graph}
            for node in graph:
                for dep in graph.get(node, []):
                    if dep in in_degree:
                        in_degree[dep] += 1

            queue = [node for node, degree in in_degree.items() if degree == 0]
            visited = set()

            while queue:
                node = queue.pop(0)
                visited.add(node)

                for neighbor in list(graph.get(node, [])):
                    if neighbor in in_degree:
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0:
                            queue.append(neighbor)

            # If topological sort visited all nodes, there are no cycles
            if len(visited) == len(self.modules):
                return []

            # Find cycles using DFS
            remaining = set(self.modules.keys()) - visited

            # Use _find_dependency_cycles from NexusCore if available
            if hasattr(self.core, "_find_dependency_cycles") and callable(self.core._find_dependency_cycles):
                return self.core._find_dependency_cycles(remaining, graph, reverse_graph)

            # Fallback implementation
            cycles = []
            cycle_visited = set()

            def find_cycle(node, path, visited_in_path):
                if node in visited_in_path:
                    # Found a cycle
                    cycle_start = path.index(node)
                    cycles.append(path[cycle_start:] + [node])
                    return

                cycle_visited.add(node)
                visited_in_path.add(node)
                path.append(node)

                for neighbor in graph.get(node, []):
                    if neighbor in remaining and neighbor not in cycle_visited:
                        find_cycle(neighbor, path, visited_in_path.copy())

                path.pop()
                visited_in_path.remove(node)

            # Try to find cycles starting from each remaining node
            for node in remaining:
                if node not in cycle_visited:
                    find_cycle(node, [], set())

            return cycles

    def get_dependency_graph_summary(self) -> Dict[str, Any]:
        """
        Creates a summary of the dependency graph structure for visualization or debugging.

        Returns:
            Dict with:
            - 'modules': list of all module names
            - 'dependencies': dict mapping module names to their dependencies
            - 'dependents': dict mapping module names to their dependents
            - 'orphaned': list of modules with no dependencies or dependents
            - 'cycles': list of dependency cycles if any
            - 'stats': general statistics about the graph
        """
        with self.lock:
            modules = list(self.modules.keys())
            dependencies = {name: list(deps) for name, deps in self.dependencies.items()}
            dependents = {name: list(deps) for name, deps in self.dependents.items()}

            # Find orphaned modules (no dependencies or dependents)
            orphaned = [name for name in modules
                        if not dependencies.get(name) and not dependents.get(name)]

            # Check for cycles
            cycles = self.check_dependency_cycles()

            # Calculate some stats
            stats = {
                "total_modules": len(modules),
                "total_dependency_links": sum(len(deps) for deps in dependencies.values()),
                "max_dependencies": max((len(deps) for deps in dependencies.values()), default=0),
                "max_dependents": max((len(deps) for deps in dependents.values()), default=0),
                "orphaned_count": len(orphaned),
                "cycles_count": len(cycles)
            }

            return {
                "modules": modules,
                "dependencies": dependencies,
                "dependents": dependents,
                "orphaned": orphaned,
                "cycles": cycles,
                "stats": stats
            }

    def discover_modules(self, package_path: str) -> List[str]:
        """
        Dynamically discover and auto-register modules from the specified Python package.

        This scans for submodules, imports them, and looks for a class whose name matches
        the submodule's last part (case-insensitive). If found, an instance is created
        and automatically registered under that name.

        Args:
            package_path (str): The dotted path to the Python package to scan.

        Returns:
            List[str]: A list of module names that were discovered and registered.
        """
        discovered = []
        try:
            package = importlib.import_module(package_path)
            if not hasattr(package, "__path__"):
                self.logger.warning(f"Package '{package_path}' has no __path__. Cannot discover submodules.")
                return discovered

            for _, submodule_name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                if is_pkg:
                    # We skip sub-packages in this example
                    continue

                try:
                    submod = importlib.import_module(submodule_name)
                    # The last element of submodule_name might be something like "some_module"
                    short_name = submodule_name.split(".")[-1].lower()

                    # Search for a class matching short_name
                    for attr_name, attr_value in vars(submod).items():
                        if inspect.isclass(attr_value):
                            if attr_name.lower() == short_name:
                                instance = attr_value()
                                # The registry name is the class name, but lowercased
                                module_name = attr_name.lower()
                                self.register(module_name, instance)
                                discovered.append(module_name)
                                break

                except Exception as e:
                    self.logger.error(f"Error loading submodule '{submodule_name}': {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Error discovering modules in '{package_path}': {e}", exc_info=True)

        if discovered:
            self.logger.info(f"Discovered and registered modules: {discovered}")
        else:
            self.logger.info(f"No modules discovered in '{package_path}'.")

        return discovered

    ############################################################
    #            INTERNAL (PROTECTED) METHODS                  #
    ############################################################

    def _set_module_state(self, name: str, state: str, error_reason: Optional[str] = None) -> None:
        """
        Protected method to change a module's state internally, recording the time
        of the change and also notifying the NexusCore if it has a suitable method.

        Args:
            name (str): The module name.
            state (str): A string in VALID_STATES.
            error_reason (str, optional): If transitioning to ERROR, explain the cause.

        Raises:
            ValueError: If the new state is not recognized.
        """
        if state not in self.VALID_STATES:
            raise ValueError(f"Invalid state '{state}'. Must be one of: {sorted(self.VALID_STATES)}")

        with self.lock:
            old_state = self.metadata.get(name, {}).get("state", "UNKNOWN")
            self.metadata.setdefault(name, {})
            self.metadata[name]["state"] = state
            self.metadata[name]["state_changed"] = time.time()
            if state == "ERROR" and error_reason:
                self.metadata[name]["error_reason"] = error_reason

            self.logger.info(f"Module '{name}' changed state: {old_state} -> {state} "
                             f"{'(reason: ' + error_reason + ')' if error_reason else ''}")

            # Attempt to update the core's view as well
            if hasattr(self.core, "update_module_status") and callable(self.core.update_module_status):
                try:
                    self.core.update_module_status(name, state)
                except Exception as e:
                    self.logger.error(f"Error updating NexusCore module status for '{name}': {e}", exc_info=True)

    def _verify_module_interface(self, name: str, module: Any) -> None:
        """
        Ensure that a module has at least a minimal set of expected methods.

        By default, we require that a module has either a 'start' method or a 'handle_message'
        method. You may expand this logic if your project demands more strict interface checks.

        Args:
            name (str): The module name for logging.
            module (Any): The module instance.

        Raises:
            ValueError: If the module doesn't have either start() or handle_message() method.
        """
        has_start = hasattr(module, "start") and callable(getattr(module, "start"))
        has_handle_message = hasattr(module, "handle_message") and callable(getattr(module, "handle_message"))
        has_stop = hasattr(module, "stop") and callable(getattr(module, "stop"))

        if not (has_start or has_handle_message):
            msg = (f"Module '{name}' provides neither start() nor handle_message(). "
                  f"It might not function properly within GrandNexus.")
            self.logger.warning(msg)
            raise ValueError(msg)

        if has_start and not has_stop:
            self.logger.warning(f"Module '{name}' has start() but no stop() method. "
                              "This may cause issues during shutdown.")

        # Check for additional recommended interfaces
        recommended_methods = {
            "get_status": "report module status",
            "set_configuration": "receive configuration updates"
        }

        for method, purpose in recommended_methods.items():
            if not (hasattr(module, method) and callable(getattr(module, method))):
                self.logger.debug(f"Module '{name}' does not implement optional '{method}()' to {purpose}")

    def _remove_dependency_links(self, name: str) -> None:
        """
        Remove any references to 'name' in the dependencies or dependents structures.

        This is typically used when a module is unregistered or re-registered.
        """
        # For each of 'name's dependencies, remove 'name' from the dep's dependents set
        deps = self.dependencies.get(name, [])
        for dep in deps:
            if dep in self.dependents and name in self.dependents[dep]:
                self.dependents[dep].remove(name)

    def _local_topo_sort(self) -> List[str]:
        """
        Perform a local topological sort of the modules using DFS, to handle dependencies
        if we can't rely on NexusCore.

        Returns:
            List[str]: A valid topological ordering (modules in the correct sequence).

        Raises:
            ValueError: If a cycle is detected.
        """
        visited = set()
        temp_visited = set()
        result = []

        def visit(node: str):
            if node in temp_visited:
                raise ValueError(f"Circular dependency detected involving '{node}'.")
            if node not in visited:
                temp_visited.add(node)
                for neighbor in self.dependencies.get(node, []):
                    if neighbor in self.modules:  # only consider known modules
                        visit(neighbor)
                temp_visited.remove(node)
                visited.add(node)
                result.append(node)

        with self.lock:
            for node in self.modules.keys():
                if node not in visited:
                    visit(node)

        # The result is reversed so that dependencies appear first
        return list(reversed(result))


