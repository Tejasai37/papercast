# Frontend UI & Templates

This directory contains the Server-Side Rendered (SSR) HTML interface for the PaperCast application. The frontend leans heavily on a vintage 1940s radio aesthetic, using custom CSS and vanilla JavaScript, securely served via FastAPI's `Jinja2Templates` engine.

## Directory Structure

*   **/templates**: The Jinja2 HTML files.
*   **/static**: The static assets (CSS, JS, Images) mounted at the `/static` path by FastAPI.

## Jinja2 HTML Templates

The UI uses a modular template inheritance design to share the vintage styling and authenticated navigation bar across all views.

*   `base.html`: The foundational template. Contains the `<head>` metadata, imports Bootstrap 5, links the custom `style.css`, and defines the `{% block content %}` area.
*   `landing.html`: The public-facing marketing page explaining the AI features and benefits.
*   `login.html`: The entry point for Amazon Cognito authentication.
*   `dashboard.html`: The primary application view. Extends `base.html`. Allows users to fetch live news, submit custom URLs, and select target languages for AI podcast generation.
*   `library.html`: The user's personal vault. Renders the DynamoDB cache records fetched by the backend, utilizing custom Jinja2 Python filters to stylize the visual script.
*   `admin.html`: A restricted view (secured by the Cognito `admins` group check in `main.py`) allowing global cache management.

## Static Assets

### `static/style.css`
Contains the custom color palette and typography that defines the "vintage radio" theme.
*   **Color Palette**: Defined as CSS variables (e.g., `--bakelite-brown`, `--dial-amber`, `--speaker-cloth`).
*   **Typography**: Uses Google Fonts (`Courier Prime` for console/typing effects, `Playfair Display` for news headers).

### `static/main.js`
Handles the client-side interactivity, DOM manipulation, and asynchronous `fetch()` calls to the FastAPI backend.
*   **Dynamic Audio Player**: Manages the custom radio dial UI, updating the frequency display during the asynchronous `/api/generate_audio` request.
*   **Regex Script Formatting**: Uses Regular Expressions (`/\[HOST([^\]]*)\]:?\s*/g`) to dynamically identify and inject CSS classes into the speaker tags (e.g., `[HOST (Matthew)]`) returned by the AI pipeline, without breaking the inline display block.
*   **Comprehend Badges**: Parses the `nlp_entities`, `nlp_key_phrases`, and `nlp_sentiment` data arrays returned by the backend to render dynamic Bootstrap 5 badges on the UI.
