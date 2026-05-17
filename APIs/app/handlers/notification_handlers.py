from app.events.bus import subscribe, Events

@subscribe(Events.BOOKING_CONFIRMED)
async def notify_vendor_of_booking(payload: dict):
    booking_id = payload["booking_id"]
    vendor_id = payload["vendor_id"]
    # await send_push_notification(vendor_id, ...)
    pass


@subscribe(Events.PAYMENT_SUCCEEDED)
async def init_chat_room(payload: dict):
    booking_id = payload["booking_id"]
    # await chat_service.create_room(...)
    pass