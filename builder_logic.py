import os
import shutil
import subprocess
import json
import xml.etree.ElementTree as ET
import re
import sys
import threading

class CordovaWrapperBuilder:
    def __init__(self, progress_callback=None, log_callback=None):
        self.progress_cb = progress_callback
        self.log_cb = log_callback
        self.aborted = False

    def log(self, message):
        if self.log_cb:
            self.log_cb(message)
        else:
            print(f"[LOG] {message}")

    def update_progress(self, percent, step_name):
        if self.progress_cb:
            self.progress_cb(percent, step_name)

    def run_command(self, cmd, cwd=None, shell=False):
        self.log(f"Running command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        try:
            # shell=True required for some npm commands on windows, but generally avoid if possible
            if sys.platform == 'win32':
                shell = True

            result = subprocess.run(
                cmd,
                cwd=cwd,
                shell=shell,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.log(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Error running command: {e}")
            self.log(e.stderr)
            return False
        except Exception as e:
            self.log(f"Exception: {e}")
            return False

    def check_dependencies(self):
        self.update_progress(0, "Checking dependencies...")

        # Check Node
        if not self.run_command(["node", "--version"]):
            self.log("Node.js is not installed. Please install Node.js.")
            return False

        # Check NPM
        if not self.run_command(["npm", "--version"]):
            self.log("NPM is not installed.")
            return False

        # Check Cordova
        if not self.run_command(["cordova", "--version"]):
            self.log("Cordova not found. Attempting to install globally...")
            if not self.run_command(["npm", "install", "-g", "cordova"]):
                self.log("Failed to install Cordova. Please run 'npm install -g cordova' manually.")
                return False

        self.log("Dependencies check passed.")
        return True

    def wrap_project(self, target_dir, dest_dir, app_name, app_id, app_version, overwrite=False):
        if not os.path.exists(target_dir):
            self.log(f"Target directory {target_dir} does not exist.")
            return False

        self.check_dependencies()

        # Step 1: Prepare Destination
        self.update_progress(10, "Preparing destination folder...")
        if os.path.exists(dest_dir):
            if not overwrite:
                self.log(f"Destination {dest_dir} exists. Aborting to prevent data loss.")
                return False

            self.log(f"Destination {dest_dir} exists. Cleaning up...")
            try:
                shutil.rmtree(dest_dir)
            except Exception as e:
                self.log(f"Could not delete destination: {e}")
                return False

        # Copy template (current directory) to destination
        # We need to exclude typical ignore files
        template_dir = os.getcwd()
        ignore_patterns = shutil.ignore_patterns(
            '.git', '.gitignore', 'node_modules', 'platforms', 'plugins',
            '*.py', '__pycache__', 'test_site', 'test_output', '.DS_Store'
        )

        try:
            shutil.copytree(template_dir, dest_dir, ignore=ignore_patterns)
        except Exception as e:
            self.log(f"Error copying template: {e}")
            return False

        # Step 2: Inject Content
        self.update_progress(30, "Injecting website content...")
        site_dest = os.path.join(dest_dir, "www", "site")
        try:
            shutil.copytree(target_dir, site_dest)
        except Exception as e:
            self.log(f"Error copying site content: {e}")
            return False

        # Step 3: Configure Project
        self.update_progress(50, "Configuring project...")
        if not self.configure_project(dest_dir, app_name, app_id, app_version):
            return False

        # Step 4: Install Dependencies (in the new project)
        self.update_progress(70, "Installing project dependencies (this may take a while)...")
        # Run npm install in dest_dir
        if not self.run_command(["npm", "install"], cwd=dest_dir):
            self.log("Warning: npm install failed. You may need to run it manually.")

        # Step 5: Prepare Cordova
        self.update_progress(85, "Preparing Cordova platform...")
        # Add android platform (as default example) or just prepare
        # Using 'cordova prepare' is safer as it uses config.xml
        # But usually you need to add a platform first.
        # Let's try adding android. If it exists or fails, we'll try prepare.

        # Note: In a real scenario, we might ask the user which platform.
        # For now, we follow the README: 'cordova platform add android'
        if not self.run_command(["cordova", "platform", "add", "android"], cwd=dest_dir):
            self.log("Warning: Could not add Android platform. Ensure Android SDK is set up.")

        # Step 6: Finalize
        self.update_progress(100, "Done!")
        return True

    def configure_project(self, dest_dir, app_name, app_id, version):
        # 1. Update config.xml
        config_path = os.path.join(dest_dir, "config.xml")
        try:
            ET.register_namespace('', "http://www.w3.org/ns/widgets")
            tree = ET.parse(config_path)
            root = tree.getroot()

            # Namespace map
            ns = {'w': 'http://www.w3.org/ns/widgets'}

            # Update id and version
            root.set('id', app_id)
            root.set('version', version)

            # Update name
            name_elem = root.find('w:name', ns)
            if name_elem is not None:
                name_elem.text = app_name

            # Update description (optional, generic)
            desc_elem = root.find('w:description', ns)
            if desc_elem is not None:
                desc_elem.text = f"Wrapped version of {app_name}"

            tree.write(config_path, encoding='UTF-8', xml_declaration=True)
        except Exception as e:
            self.log(f"Error updating config.xml: {e}")
            return False

        # 2. Update package.json
        pkg_path = os.path.join(dest_dir, "package.json")
        try:
            with open(pkg_path, 'r') as f:
                data = json.load(f)

            data['name'] = app_id.lower().replace('.', '-')
            data['displayName'] = app_name
            data['version'] = version
            data['description'] = f"Wrapped version of {app_name}"

            with open(pkg_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.log(f"Error updating package.json: {e}")
            return False

        # 3. Patch www/js/index.js
        js_path = os.path.join(dest_dir, "www", "js", "index.js")
        try:
            with open(js_path, 'r') as f:
                content = f.read()

            # We need to change LANDING_URL and SPLIT_URL_RE

            # Replace LANDING_URL
            # Strategy: We make LANDING_URL dynamic based on location to support file://

            new_landing_logic = """
var LANDING_PATH = "site/index.html";
// Resolve absolute path for local file usage
var path = window.location.pathname;
var root = path.substring(0, path.lastIndexOf('/') + 1);
var LANDING_URL = root + LANDING_PATH;
"""
            # Regex to find the original LANDING_URL line
            new_content = re.sub(
                r'var\s+LANDING_URL\s*=\s*".*?";',
                new_landing_logic,
                content,
                count=1
            )

            if new_content == content:
                self.log("Error: Could not patch LANDING_URL in index.js. Regex did not match.")
                return False
            content = new_content

            # Replace SPLIT_URL_RE to support file:// (allow empty host)
            # Original: var SPLIT_URL_RE = /^([^:/]+:\/\/[^/]+)(\/[^?]*)(?:\?([^#]*))?(?:#(.*))?$/i;
            # New:      var SPLIT_URL_RE = /^((?:[^:/]+:\/\/[^/]*)?)(\/[^?]*)(?:\?([^#]*))?(?:#(.*))?$/i;
            # Note the * instead of + in the second part of group 1, and optional group 1

            new_regex = r'var SPLIT_URL_RE = /^((?:[^:/]+:\/\/[^/]*)?)(\/[^?]*)(?:\?([^#]*))?(?:#(.*))?$/i;'

            new_content = re.sub(
                r'var\s+SPLIT_URL_RE\s*=.*;',
                new_regex,
                content,
                count=1
            )

            if new_content == content:
                self.log("Error: Could not patch SPLIT_URL_RE in index.js. Regex did not match.")
                return False
            content = new_content

            with open(js_path, 'w') as f:
                f.write(content)

        except Exception as e:
            self.log(f"Error patching index.js: {e}")
            return False

        return True

if __name__ == "__main__":
    # Test run
    print("This is the logic module. Run builder_gui.py to use the application.")
