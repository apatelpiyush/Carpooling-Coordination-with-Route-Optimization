# User Guide

## 1. Introduction

CarpoolConnect supports users who want to publish rides as drivers or reserve seats as passengers. A driver account can also book another driver's ride; the two activities are available through separate navigation pages.

## 2. Registration

1. Open the application home page.
2. Select **Get Started** or **Register**.
3. Enter name, email, phone number, and password.
4. Choose whether the account is a driver.
5. Submit the form.
6. Use the registered email and password to log in.

Passwords must contain at least eight characters according to the registration API. Email and phone values must be unique.

## 3. Login and logout

1. Open the Login page.
2. Enter registered email and password.
3. On successful login, the dashboard opens.
4. Select **Logout** to end the session.

## 4. Driver: register a vehicle

1. Log in with a driver account.
2. Open the dashboard's vehicle section.
3. Enter vehicle make, model, registration/plate number, capacity, and optional color.
4. Submit the vehicle details.
5. Confirm the vehicle appears in the vehicle list.

Vehicle capacity is constrained to 1–8 seats by the database.

## 5. Driver: publish a ride

1. Select the ride publishing option from the dashboard.
2. Choose one of your registered vehicles.
3. Enter source and destination.
4. Select departure date/time.
5. Set available seats and price per seat.
6. Provide source and destination map coordinates through the location interface.
7. Submit the ride.
8. Verify the ride appears in My Rides.

## 6. Search for rides

1. Open **Find Rides**.
2. Enter source and destination for a standard search, or use the nearby matching interface.
3. For nearby matching, select pickup and drop-off locations on the map/search interface.
4. Review matching rides, available seats, driver information, price, and detour details.
5. Open a ride to view its details.

Exact matching compares source and destination names. Nearby matching uses coordinates, vector candidate ranking, and route-insertion/detour validation.

## 7. Book a ride

1. Open the selected ride's details.
2. Choose pickup and drop-off points.
3. Enter the number of seats.
4. Review the detour information and confirm the booking.
5. A successful booking is shown in **My Bookings**.
6. The booked seat count is deducted from the ride's available seats.

A user cannot book their own ride. A booking is rejected if the ride is cancelled, departed, or does not have sufficient seats.

## 8. My Bookings

1. Open **My Bookings** from the navigation bar.
2. Review rides booked by the current account.
3. Open the relevant booking to review its information.
4. Cancel a confirmed booking when cancellation is permitted.

A driver account also has access to My Bookings when it books another driver's ride.

## 9. Driver: Passenger Bookings

1. Log in with a driver account.
2. Open **Passenger Bookings**.
3. Review passengers who booked rides published by the current driver.
4. Review booking status, seat count, pickup/drop locations, and passenger contact details.

This page is different from My Bookings: it lists bookings made by passengers on rides owned by the logged-in driver.

## 10. My Rides: edit and cancel

1. Open the dashboard's My Rides section.
2. Find a scheduled ride.
3. Use **Edit** to update departure time, available seats, or price per seat.
4. Use **Cancel** to cancel an eligible ride.

The current backend prevents editing or cancelling a ride that has confirmed bookings. Only the owning driver can manage the ride.

## 11. Notifications

1. Select the notification icon in the navigation bar.
2. Review recent booking notifications.
3. Select a notification to mark it as read.
4. Use Refresh if you want to reload the list.

Notifications include booking confirmation, new passenger booking, booking cancellation, and passenger cancellation events. The application polls for updates periodically in the browser.

## 12. Common issues

| Issue | What to check |
|---|---|
| Cannot log in | Check email/password and account registration |
| Page redirects to login | Log in; the page requires a session |
| Passenger Bookings unavailable | Confirm the account is registered as a driver |
| No rides found | Check route names, departure date, ride status, and available seats |
| Nearby match not found | Check selected coordinates and detour limit |
| Booking rejected | Check available seats, departure time, ride status, and pickup/drop feasibility |
| Ride cannot be edited/cancelled | It may have confirmed bookings or may not be scheduled |
| Notifications not loading | Check login session and notification database migration |

## 13. Safe usage

- Do not share your password.
- Confirm pickup/drop locations before booking.
- Check departure time, seats, and price before confirming.
- Use only your own account to view and manage bookings.
