# Kanto Collect - Task Tracker

## 🎯 Current Focus: Deal Analyzer UI (Pre-Travel Sprint)

**Goal**: Get Deal Analyzer UI working before travel for on-the-go deal evaluation

---

## ✅ Completed Tasks

- [x] Project planning and architecture design
- [x] PriceCharting Legendary subscription obtained
- [x] Folder structure created
- [x] Environment variables configured
- [x] Backend foundation (FastAPI, SQLite, Auth)
- [x] User model and JWT authentication
- [x] PriceCharting API integration
- [x] Deal Analyzer backend service
- [x] Price lookup endpoints working

---

## 🔥 Phase 1: Deal Analyzer (HIGH PRIORITY - Before Travel)

### Backend ✅ Complete
- [x] PriceCharting API client
- [x] Price lookup by product name
- [x] Search products endpoint
- [x] Authentication & admin protection

### AI Integration (Next)
- [ ] Claude Vision integration for card detection
- [ ] Image upload handling
- [ ] Card identification from photos
- [ ] Multi-card lot detection

### UI (Priority)
- [ ] Simple web interface for Deal Analyzer
- [ ] Image upload component
- [ ] Price lookup form
- [ ] Results display
- [ ] Mobile-friendly design

---

## 📦 Phase 2: Inventory Tool

### Core Features
- [ ] Product model and database
- [ ] CRUD endpoints for products
- [ ] Category management
- [ ] Stock level tracking
- [ ] Low stock alerts

### Scanning
- [ ] Barcode scanner integration
- [ ] Quick lookup by UPC
- [ ] Fast add to inventory

### UI
- [ ] Product list view
- [ ] Add/Edit forms
- [ ] Search and filters
- [ ] Dashboard with stats

---

## 📅 Phase 3: Calendar & Task Management (NEW)

### User Management
- [ ] Extend user model with roles (Admin, Manager, Team Member)
- [ ] Team invitation system
- [ ] User permissions

### Calendar
- [ ] Event model (shows, deadlines, etc.)
- [ ] Calendar API endpoints
- [ ] Create/edit/delete events
- [ ] Recurring events

### Task Management
- [ ] Task model with assignments
- [ ] Task API endpoints
- [ ] Assign tasks to team members
- [ ] Task status tracking (todo, in progress, done)
- [ ] Due dates and reminders

### Show Prep
- [ ] Link inventory items to shows
- [ ] Prep checklist per show
- [ ] "Items needed" tracking
- [ ] Post-show reconciliation

### UI
- [ ] Calendar view (month/week/day)
- [ ] Task board (Kanban style)
- [ ] My Tasks personal view
- [ ] Show prep checklist view
- [ ] Team overview dashboard

### Future Integrations
- [ ] Google Calendar sync
- [ ] Email notifications
- [ ] Discord notifications

---

## 🔗 Phase 4: Whatnot Integration (When API Ready)

- [ ] Request Whatnot API access (DO THIS NOW)
- [ ] Implement Whatnot API client
- [ ] Sync inventory with Whatnot
- [ ] Track live sale deductions
- [ ] Import show schedules to calendar

---

## 🤖 Phase 5: Discord Scalper Bot

- [ ] Discord bot setup
- [ ] Channel monitoring
- [ ] Alert parsing
- [ ] Auto-purchase logic (optional)
- [ ] Deal notifications to team

---

## 🛒 Phase 6: Online Store (Shopify - When Ready)

**Only after Whatnot system is perfected!**

- [ ] Set up Shopify store
- [ ] Connect PriceCharting Shopify integration
- [ ] Configure price sync rules
- [ ] Design store (Lovable)
- [ ] Launch

---

## 🐛 Discovered During Work

- [x] JWT token decode fix (sub must allow integer)
- [x] Database path fix (load .env from parent directory)
- [ ] PriceCharting search returns mixed categories (need filtering)

---

## 📅 Timeline

| Phase | Target | Status |
|-------|--------|--------|
| Phase 1 - Deal Analyzer | Before Travel | 🔄 In Progress |
| Phase 2 - Inventory | After Travel | ⏳ Pending |
| Phase 3 - Calendar/Tasks | After Inventory | ⏳ Pending |
| Phase 4 - Whatnot | When API Ready | ⏳ Blocked |
| Phase 5 - Discord Bot | TBD | ⏳ Pending |
| Phase 6 - Shopify Store | Last Priority | ⏳ Pending |

---

## 👥 Team Structure

| Person | Role | Primary Tools |
|--------|------|---------------|
| TBD | Admin | All tools |
| TBD | Team Member | Tasks, Inventory |
| TBD | Team Member | Tasks, Inventory |

*Roles and assignments to be configured in the system*
