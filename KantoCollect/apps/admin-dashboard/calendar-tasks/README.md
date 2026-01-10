# 📅 Calendar & Task Management System

Team coordination tool for managing shows, inventory prep, and task assignments.

## Purpose

Coordinate a team of 3+ people to:
- Schedule and prepare for Whatnot shows
- Track inventory needed for upcoming events
- Assign and monitor tasks
- Never miss deadlines

## Core Features

### 📆 Calendar
- View all upcoming shows/events
- See who's working when
- Color-coded by event type
- Sync with Google Calendar (future)

### ✅ Task Management
- Create tasks with deadlines
- Assign to team members
- Track completion status
- Recurring tasks (e.g., weekly inventory check)

### 👥 Team Features (3 users, scalable)
- User accounts with roles
- Personal task lists
- Team-wide visibility
- Activity log

### 📦 Show Prep
- Link inventory to shows
- "Items needed" checklist
- Prep status tracking
- Post-show inventory reconciliation

## User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access, manage users, all settings |
| **Manager** | Create events, assign tasks, view all |
| **Team Member** | View assigned tasks, update status |

## Planned Views

1. **Calendar View** - Month/week/day view of all events
2. **Task Board** - Kanban-style task management
3. **My Tasks** - Personal task list for each user
4. **Show Prep** - Checklist view for upcoming shows
5. **Team Overview** - Who's doing what

## API Endpoints (Planned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/calendar/events` | List all events |
| POST | `/api/v1/admin/calendar/events` | Create event |
| GET | `/api/v1/admin/tasks` | List tasks |
| POST | `/api/v1/admin/tasks` | Create task |
| PUT | `/api/v1/admin/tasks/{id}/assign` | Assign task |
| PUT | `/api/v1/admin/tasks/{id}/complete` | Mark complete |
| GET | `/api/v1/admin/shows` | List shows |
| POST | `/api/v1/admin/shows/{id}/prep` | Add prep items |

## Integration Points

- **Inventory Tool**: Link items to show prep
- **Whatnot**: Sync show schedules (future)
- **Google Calendar**: Two-way sync (future)
- **Notifications**: Email/Discord alerts (future)

---

## 📅 Weekly Show Schedule (Pre-configured)

Based on your current Whatnot schedule:

| Day | Show | Key Items Needed |
|-----|------|------------------|
| **Thursday** | 🎡 Spin The Wheel | 6 Korean Boxes, 2 High-Tier, 10 Mid-Tier, 38 Floor Prizes |
| **Friday** | 💵 Dollar & MSRP Auctions | 50-100 Packs, 5-10 Chaser Packs, 2 Korean Boxes |
| **Saturday** | 🃏 Single Auctions | 50-100 Mid/High Single Cards |

**Weekly Supply Cost: ~$2,402**

### Automated Prep Checklists

The Calendar system will generate prep tasks like:
- [ ] **Wednesday**: Count Thursday inventory, verify prize pool
- [ ] **Thursday AM**: Label 300 items, prep bubble wrap
- [ ] **Thursday PM**: Run Spin The Wheel show
- [ ] **Friday AM**: Prep Friday packs, verify chaser inventory
- [ ] **Friday PM**: Run Dollar & MSRP Auctions
- [ ] **Saturday AM**: Pull Saturday singles, top-load all cards
- [ ] **Saturday PM**: Run Single Auctions
- [ ] **Sunday-Tuesday**: Ship all orders, restock for next week

---

*Development will begin after Inventory Tool is complete.*
