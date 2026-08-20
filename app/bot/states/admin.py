from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    import_status = State()
    import_departure_date = State()
    import_expected_at = State()
    import_file = State()
    import_confirmation = State()
    parcel_search = State()
    parcel_status = State()
    parcel_sent_at = State()
    parcel_expected_at = State()
    user_search = State()
    user_add_name = State()
    user_add_phone = State()
    user_add_code = State()
    user_edit_value = State()
    broadcast_text = State()
    broadcast_confirm = State()
    setting_value = State()
