
# Instructions to Run `panshemlumus.py` in Ubuntu WSL

## Step 1: Ensure Python is Installed

1. **Check Python Installation**:
   ```bash
   python3 --version
   ```

2. **Install Python (if necessary)**:
   ```bash
   sudo apt update
   sudo apt install python3
   sudo apt install python3-pip
   ```

## Step 2: Set Up a Virtual Environment (optional but recommended)

1. **Navigate to Your Project Directory**:
   ```bash
   cd /mnt/d/path/to/your/git/repository
   ```

2. **Create a Virtual Environment**:
   ```bash
   python3 -m venv myenv
   ```

3. **Activate the Virtual Environment**:
   ```bash
   source myenv/bin/activate
   ```

## Step 3: Install Dependencies

1. **Install Required Packages**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 4: Run Your Python Script

1. **Run the Python File**:
   ```bash
   python3 panshemlumus.py
   ```

## Example Workflow

1. **Open Ubuntu Terminal**:
   ```bash
   cd /mnt/d/path/to/your/git/repository
   ```

2. **Activate the Virtual Environment**:
   ```bash
   source myenv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Python File**:
   ```bash
   python3 panshemlumus.py
   ```

By following these steps, you should be able to run your Python script `panshemlumus.py` within your WSL environment.
