# GEMINI.md

## Project Overview

This project is a multi-tenant ERP (Enterprise Resource Planning) system built with Django. It is designed to manage sales, inventory, and orders for multiple companies, with each company's data being isolated in a multi-tenancy architecture. The system uses a PostgreSQL database and is set up for deployment with Gunicorn and Whitenoise.

The project is structured into several Django apps, each responsible for a specific domain:

-   `accounts`: Manages user authentication and profiles.
-   `catalog`: Handles product and category management.
-   `core`: Contains the core logic and views of the application, including the main dashboard and system settings.
-   `inventory`: Manages stock and inventory-related operations.
-   `orders`: Handles customer orders.
-   `p_v`: The main Django project directory, containing the settings and root URL configuration.
-   `p_v_App`: The central app that orchestrates the other apps and contains the core data models and multi-tenancy logic.
-   `sales`: Manages sales transactions.
-   `staff`: Manages staff and waiter information.
-   `tables`: Manages restaurant tables and table orders.

## Building and Running

### Prerequisites

-   Python 3
-   PostgreSQL

### Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd ERP-FortTech-main
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the database:**

    The project is configured to use a PostgreSQL database. The connection settings are defined in `p_v/settings.py` using `dj_database_url`. Make sure you have a PostgreSQL server running and update the `DATABASE_URL` environment variable if necessary.

5.  **Run the database migrations:**

    ```bash
    python manage.py migrate
    ```

### Running the Development Server

To run the development server, use the following command:

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

### Testing

To run the tests, use the following command:

```bash
python manage.py test
```

## Development Conventions

-   **Multi-Tenancy:** The application is built with a multi-tenancy architecture. Each company's data is isolated using a `Company` model and a `TenantMiddleware`. All new models that should be company-specific must use the `TenantMixin` and the `TenantManager`.
-   **Coding Style:** The project uses `ruff` for linting. It is recommended to run `ruff check .` before committing changes.
-   **Static Files:** Static files are handled by `whitenoise`. They are located in the `static` directory and collected into the `staticfiles` directory for production.
-   **Templates:** Templates are located in the `templates` directory of each app. The base template is in `core/templates/core/base.html`.
