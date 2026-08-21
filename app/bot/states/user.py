from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    full_name = State()


class LinkStates(StatesGroup):
    client_code = State()
    full_name = State()


class TrackingStates(StatesGroup):
    tracking_number = State()
