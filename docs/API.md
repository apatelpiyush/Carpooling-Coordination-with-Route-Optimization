# API Reference

All API responses are JSON unless otherwise noted. Authentication is session-cookie based. Login sets the Flask session; browser requests should retain the session cookie.

## Authentication — `/auth`

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Create account |
| POST | `/auth/login` | Public | Authenticate and create session |
| POST | `/auth/logout` | Session recommended | Clear session |
| GET | `/auth/me` | Logged in | Return current account |

### Registration request

```json
{
  "name": "Example User",
  "email": "user@example.com",
  "phone": "9999999999",
  "password": "example-password",
  "is_driver": true
}
```

Returns `201` on success, `400` for validation errors, and `409` for duplicate email/phone.

### Login request

```json
{
  "email": "user@example.com",
  "password": "example-password"
}
```

Returns `200` on success, `400` for missing fields, and `401` for invalid credentials.

## Vehicles — `/api`

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/api/vehicles` | Logged-in driver | Register a vehicle |
| GET | `/api/vehicles` | Logged-in driver | List current driver's vehicles |

Vehicle creation fields are `make`, `model`, `plate_number`, `capacity`, and optional `color`. The current driver identity is taken from the session.

## Rides — `/api`

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/api/rides` | Logged-in driver | Publish ride |
| GET | `/api/rides` | Public endpoint in code | Search scheduled future rides; optional `source`, `destination` query parameters |
| GET | `/api/rides/match` | Public endpoint in code | Exact source/destination matching |
| GET | `/api/rides/match-nearby` | Public endpoint in code | Nearby route matching using coordinates |
| GET | `/api/my-rides` | Logged-in driver | List current driver's rides |
| PUT | `/api/rides/{ride_id}` | Owning driver | Edit scheduled ride without confirmed bookings |
| POST | `/api/rides/{ride_id}/cancel` | Owning driver | Cancel scheduled ride without confirmed bookings |
| GET | `/api/rides/{ride_id}/details` | Logged-in user | Ride, driver, vehicle, and stop details |

### Nearby matching query parameters

Required:
- `pickup_lat`
- `pickup_lon`
- `drop_lat`
- `drop_lon`

Optional:
- `radius_km` (default 5; accepted range greater than 0 and at most 50)
- `max_detour_km` (optional; accepted range 0 through 500)

### Ride edit request

```json
{
  "departure_time": "2030-05-20T10:30:00",
  "available_seats": 3,
  "price_per_seat": 150
}
```

The supplied implementation rejects timezone-aware datetime strings and requires a future local datetime. Only scheduled rides with no confirmed bookings can be edited. Seats cannot exceed vehicle capacity.

## Bookings — `/api`

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/api/bookings` | Logged-in user | Book seats and insert pickup/drop into route |
| GET | `/api/bookings` | Logged-in user | List current user's bookings |
| POST | `/api/bookings/{booking_id}/cancel` | Booking owner | Cancel own confirmed booking |
| GET | `/api/driver/bookings` | Logged-in driver | List bookings on rides owned by current driver |

### Booking request

```json
{
  "ride_id": 123,
  "seats_booked": 1,
  "pickup_name": "Pickup point",
  "pickup_lat": 18.5204,
  "pickup_lon": 73.8567,
  "drop_name": "Drop point",
  "drop_lat": 19.0760,
  "drop_lon": 72.8777,
  "max_detour_km": 20
}
```

The booking endpoint validates coordinate ranges, non-identical pickup/drop coordinates, positive seat count, ride status, departure time, available seats, and route insertion feasibility. It returns `201` when the booking is created.

A user cannot book their own ride. The ride row is locked during booking to prevent simultaneous overbooking.

## Notifications — `/api`

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/api/notifications` | Logged in | Return latest 50 notifications and unread count |
| POST | `/api/notifications/{notification_id}/read` | Notification owner | Mark notification as read |

Notification creation is performed by a database trigger in the development database. The trigger DDL is not present in the supplied ZIP.

## Common status codes

| Status | Meaning |
|---|---|
| 200 | Request completed |
| 201 | Resource created |
| 400 | Invalid input or operation not allowed |
| 401 | Login required or invalid credentials |
| 403 | Authenticated user lacks required role |
| 404 | Requested resource not found or not owned by user |
| 409 | Conflict, such as duplicate registration or ride with confirmed bookings |
| 500 | Unexpected server-side error |

Exact response messages may vary by endpoint. Use the source code as the definitive contract when extending the API.
