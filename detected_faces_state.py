class DetectedFacesState:
    def __init__(self):
        self.faces = {}  # Dictionary to store detected faces per session

    def init_session(self, session_id):
        """Initialize a new session if it doesn't exist"""
        if session_id not in self.faces:
            self.faces[session_id] = set()

    def add_face(self, session_id, student_id):
        """Add a detected face to a session"""
        self.init_session(session_id)
        self.faces[session_id].add(student_id)

    def is_detected(self, session_id, student_id):
        """Check if a face was detected in a session"""
        self.init_session(session_id)
        return student_id in self.faces[session_id]

    def clear_session(self, session_id):
        """Clear all detected faces for a session"""
        self.faces[session_id] = set()

    def clear_all(self):
        """Clear all detected faces from all sessions"""
        self.faces = {}

detected_faces_state = DetectedFacesState() 