# lifescore-score/ms

Project Setup
install Gcloud CLI
Install Docker
You must have ssh keys with github
A new age is upon us.

1. Clone the main repository

2. Create virtual environment, install dependencies, and install hooks. It may vary depending on your OS.

    ```bash
        python -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        chmod +x hooks/*
        python install_hooks.py
    ```

3. Initialize and update submodules

    ```bash
        git submodule init
        git submodule update
        chmod +x switch-branch.sh
        ./switch-branch.sh development
    ```

4. Use the switch-branch script to get to your desired branch
Make the script executable first

    ```bash
       ./switch-branch.sh development
    ```

5. You must have installed the gcloud CLI and authenticate to the project where the services are deployed. You must generate the credentials using the gcloud CLI and copying your the credentials to key.json on the root folder.

    ```bash
        gcloud auth login
        gcloud config set project "project-id"
        gcloud auth application-default login
    ```

6. Configure pre commit

    ```bash
        pre-commit install --install-hooks
        pre-commit autoupdate
        pre-commit run --all-files
    ```

7. Generate migration in the shared_db submodule always checking on the varibles in the .env file, everytime you change a variable in the .env file, you must create a new terminal. Migrations is for local development.

    ```bash
        generate_migration.sh "Name of the migration"
    ```

8. Run migration in the shared_db submodule always checking on the varibles in the .env file, everytime you change a variable in the .env file, you must create a new terminal. Migrations is for local development.

    ```bash
        run_migration.sh
    ```

9. Run the app in development mode connecting to containerized local database and redis. You can restart the container without rebuilding it.

    ```bash
        docker-compose --profile local up --build
    ```

10. Create .env file for development

    ```bash
        op inject -i env.dev.tpl -o .env
    ```
