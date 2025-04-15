
    document.getElementById('roleForm').addEventListener('submit', function(event) {
        event.preventDefault();

        var role = document.getElementById('role').value;

        var urlMapping = {
            'department_head': "{% url 'department_head_create' %}",
            'advisor': "{% url 'add_advisor' %}",
            'student': "{% url 'add_student' %}",
            'supervisor': "{% url 'supervisor_register' %}",
            'company_admin': "{% url 'company_admin_create' %}"
        };

        window.location.href = urlMapping[role];
    });

