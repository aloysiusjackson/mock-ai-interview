const API_BASE_URL = '/api';

const api = {
    async getRoles() {
        try {
            const res = await fetch(`${API_BASE_URL}/roles`);
            if (!res.ok) throw new Error('Failed to fetch roles');
            return await res.json();
        } catch (error) {
            console.error('Error fetching roles:', error);
            return { roles: ['Software Engineer', 'Product Manager', 'Data Analyst'] }; // Fallback
        }
    },

    async getQuestions(role) {
        try {
            const res = await fetch(`${API_BASE_URL}/questions?role=${encodeURIComponent(role)}`);
            if (!res.ok) throw new Error('Failed to fetch questions');
            return await res.json();
        } catch (error) {
            console.error('Error fetching questions:', error);
            throw error;
        }
    },

    async submitInterview(role, answers) {
        try {
            const res = await fetch(`${API_BASE_URL}/submit-interview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ role, answers })
            });
            if (!res.ok) throw new Error('Failed to submit interview responses');
            return await res.json();
        } catch (error) {
            console.error('Error submitting interview responses:', error);
            throw error;
        }
    },

    async getDashboard() {
        try {
            const res = await fetch(`${API_BASE_URL}/dashboard`);
            if (!res.ok) throw new Error('Failed to load dashboard metrics');
            return await res.json();
        } catch (error) {
            console.error('Error loading dashboard metrics:', error);
            throw error;
        }
    },

    async getInterviewDetail(id) {
        try {
            const res = await fetch(`${API_BASE_URL}/interview/${id}`);
            if (!res.ok) throw new Error(`Failed to load interview ${id} details`);
            return await res.json();
        } catch (error) {
            console.error(`Error loading interview ${id} details:`, error);
            throw error;
        }
    },

    async autoGrade(data) {
        try {
            const res = await fetch(`${API_BASE_URL}/auto-grade`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!res.ok) throw new Error('Failed to auto-grade response');
            return await res.json();
        } catch (error) {
            console.error('Error auto-grading response:', error);
            throw error;
        }
    }
};
