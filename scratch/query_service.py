
class QueryService:
    def get_user_data(self, user_id):
        self.last_accessed = user_id  # Violation: assignment inside 'get_' method
        return {"id": user_id}
