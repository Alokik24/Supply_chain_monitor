Host Machine
  └── docker compose up

Docker Network
  ├── web
  │    └── FastAPI
  │
  ├── database
  │    └── PostgreSQL
  │
  └── cache
       └── Redis

Host → Postgres
localhost:5432

Web Container → Postgres
database:5432