# Wiki App

A collaborative knowledge management platform with multi-role access control.

## Features

### Content Management
- **Pages** - Rich text documents with hierarchical organization (pages can have subpages)
- **Folders** - Organize pages into nested folder structures
- **Rich Text Editor** - BlockNote editor with formatting, lists, headings
- **Auto-save** - Content saves automatically with debounce
- **Soft Deletes** - Deleted content can be recovered

### Access Control (Multi-Role RBAC)
- Users can have multiple roles simultaneously
- **System Roles**: superadmin, admin, member, public
- **Custom Roles**: Create additional roles as needed
- **Permission Levels**: VIEW, EDIT, MANAGE
- **Permission Inheritance**: Page permissions inherit from parent folder
- **Public Content**: Folders/pages can be marked public for unauthenticated access

### User Management
- Email/password authentication with JWT tokens
- Admin panel for user management
- Assign/remove multiple roles per user
- View user role assignments

### Settings
- Site name configuration
- Home page selection
- Allow/disallow zero-role users

### Data Export
- Export all content to ZIP file via `/export` endpoint

## Directory Structure

```
app/wiki/
├── backend/
│   ├── app/
│   │   ├── main.py           # App entry, startup, core routes
│   │   ├── db.py             # Database config
│   │   ├── models.py         # ORM models
│   │   ├── schemas.py        # Request/response schemas
│   │   ├── auth.py           # JWT auth dependencies
│   │   ├── services.py       # Permission checking logic
│   │   └── api/              # Route handlers
│   └── tests/
└── frontend/
    └── src/
        ├── app/
        │   ├── wiki-layout.tsx      # Main layout with sidebar
        │   ├── page/[id]/page.tsx   # Page editor
        │   ├── admin/page.tsx       # Admin panel
        │   └── login/page.tsx       # Login form
        └── components/
```

## Development Commands

### Backend
```bash
cd app/wiki/backend
uv sync                              # Install dependencies
uv run uvicorn app.main:app --reload # Start server (:8000)
uv run pytest -v                     # Run tests
```

### Frontend
```bash
cd app/wiki/frontend
yarn install    # Install dependencies
yarn dev        # Start server (:3000)
yarn build      # Production build
```

## Environment Variables

Set in `.env` file or environment:
- `DATABASE_URL` - Database connection (default: SQLite `wiki.db`)
- `SECRET_KEY` - JWT signing key
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - OAuth (optional)

## Current Development Phase

**Phase 11**: Multi-role RBAC system
- Users can now have multiple roles
- Role management UI in admin panel
- Updated permission checking for multi-role scenarios
