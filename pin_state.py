class PinState:
    def __init__(self):
        self.expected_pin = None
        self.current_student_id = None
        self.current_session_id = None
        self.waiting_for_pin = False
        self.current_pin = ""

pin_state = PinState() 