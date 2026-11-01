# Testing Documentation

## 1. Purpose

This document provides a repeatable test plan for authentication, authorization, ride management, route matching, bookings, concurrency, notifications, and database integrity.

The project team reported that the functional and security test cases below were completed successfully during development. Re-run them against the final database and application build before submission. Record the actual run date, tester, test data, and evidence screenshots.

## 2. Test environment

Record the exact values used for the final test run:

| Item | Value |
|---|---|
| OS | To be recorded |
| Python version | To be recorded |
| Flask version | 3.1.3 in supplied requirements |
| PostgreSQL version | To be recorded |
| pgvector version | To be recorded |
| Browser | To be recorded |
| Test database | `carpool` (development configuration) |

## 3. Authentication and authorization

| ID | Test | Expected result |
|---|---|---|
| AUTH-01 | Register a new rider | Account created |
| AUTH-02 | Register a new driver | Account created |
| AUTH-03 | Register with duplicate email/phone | Conflict response |
| AUTH-04 | Login with valid credentials | Session established |
| AUTH-05 | Login with invalid password | HTTP 401; no authenticated session |
| AUTH-06 | Submit SQL-injection-style login input | Authentication rejected |
| AUTH-07 | Access protected API while logged out | HTTP 401 |
| AUTH-08 | Rider opens driver-only Passenger Bookings page/API | Access denied or redirected |
| AUTH-09 | Driver opens Passenger Bookings | Access granted |
| AUTH-10 | Driver opens My Bookings | Access granted |
| AUTH-11 | Logout then access protected API | HTTP 401 |

## 4. Vehicle and ride management

| ID | Test | Expected result |
|---|---|---|
| RIDE-01 | Driver registers vehicle | Vehicle stored |
| RIDE-02 | Driver lists own vehicles | Only own vehicles returned |
| RIDE-03 | Driver publishes valid ride | Ride and route stops created |
| RIDE-04 | Search scheduled rides | Future rides with seats returned |
| RIDE-05 | Exact source/destination search | Exact matches returned |
| RIDE-06 | Driver views My Rides | Own rides returned |
| RIDE-07 | Edit scheduled ride without confirmed bookings | Updated successfully |
| RIDE-08 | Cancel scheduled ride without confirmed bookings | Status becomes cancelled |
| RIDE-09 | Edit ride with confirmed bookings | Rejected |
| RIDE-10 | Cancel ride with confirmed bookings | Rejected |
| RIDE-11 | Attempt to book cancelled ride | Rejected |

## 5. Route matching

| ID | Test | Expected result |
|---|---|---|
| ROUTE-01 | Submit valid nearby pickup/drop coordinates | Nearby candidates evaluated |
| ROUTE-02 | Submit invalid latitude/longitude | HTTP 400 |
| ROUTE-03 | Submit radius outside allowed range | HTTP 400 |
| ROUTE-04 | Request with a feasible detour | Valid route match returned |
| ROUTE-05 | Request where no valid insertion is found | No match / validation error |
| ROUTE-06 | Inspect returned detour | Original, modified, and detour distances are provided where a match is returned |
| ROUTE-07 | Verify route embedding after route change | Stored vector regenerated |

## 6. Booking and concurrency

| ID | Test | Expected result |
|---|---|---|
| BOOK-01 | Book available seats | Confirmed booking created |
| BOOK-02 | Book more seats than available | Rejected |
| BOOK-03 | Book own ride | Rejected |
| BOOK-04 | Book ride that has departed | Rejected |
| BOOK-05 | Cancel own confirmed booking | Status cancelled; seats restored |
| BOOK-06 | Cancel same booking again | Rejected |
| BOOK-07 | Cancel another user's booking | Not found / denied |
| BOOK-08 | Two users simultaneously request the final seat | At most one booking succeeds |
| BOOK-09 | Driver edits/cancels ride with confirmed booking | Operation rejected |

The booking endpoint uses row-level locking on the ride row and performs seat reduction, route update, embedding regeneration, and booking insertion in one transaction.

## 7. Notifications

| ID | Test | Expected result |
|---|---|---|
| NOTIF-01 | Create confirmed booking | Rider receives confirmation notification |
| NOTIF-02 | Create confirmed booking | Ride driver receives new-passenger notification |
| NOTIF-03 | Cancel confirmed booking | Rider receives cancellation notification |
| NOTIF-04 | Cancel confirmed booking | Driver receives passenger-cancelled notification |
| NOTIF-05 | Fetch notifications while logged out | HTTP 401 |
| NOTIF-06 | Fetch notifications while logged in | Only current user's notifications returned |
| NOTIF-07 | Mark own notification read | `is_read` becomes true |
| NOTIF-08 | Mark another user's notification read | Not found / denied |

## 8. Database integrity checks

Run these checks after testing:

```sql
-- Check for bookings with missing rides.
SELECT b.booking_id
FROM bookings b
LEFT JOIN rides r ON r.ride_id = b.ride_id
WHERE r.ride_id IS NULL;

-- Check for stops with missing rides.
SELECT s.stop_id
FROM stops s
LEFT JOIN rides r ON r.ride_id = s.ride_id
WHERE r.ride_id IS NULL;

-- Check extension.
SELECT extname
FROM pg_extension
WHERE extname = 'vector';

-- Check indexes.
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

Expected orphan-query result: zero rows. The vector extension and required indexes should be present.

## 9. Security checks

- Parameterized SQL is used for user-provided values.
- Passwords are stored using Werkzeug password hashing.
- Protected endpoints check the session.
- Driver-only operations verify driver role and ownership.
- Booking cancellation verifies booking ownership.
- Notification reads/updates are scoped to the logged-in user.

The SQL-injection tests are basic input validation checks, not a complete security audit. Before production, also review CSRF protection, cookie flags, rate limiting, input length limits, error handling, dependency vulnerabilities, and deployment configuration.

## 10. Test execution record

Complete this table during the final test run:

| Test ID / group | Actual result | Pass/Fail | Evidence file |
|---|---|---|---|
| Authentication | To be recorded | To be recorded | Screenshot/log |
| Ride management | To be recorded | To be recorded | Screenshot/log |
| Route matching | To be recorded | To be recorded | Screenshot/log |
| Booking/concurrency | To be recorded | To be recorded | Screenshot/log |
| Notifications | To be recorded | To be recorded | Screenshot/log |
| Database integrity | To be recorded | To be recorded | SQL output |

Do not mark a test as passed in a formal submission unless it was executed on the submitted version.
