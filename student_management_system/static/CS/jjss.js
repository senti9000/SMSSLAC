document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');

    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }
});

    // Automatically submit the form when the user types in the search input
    document.getElementById('form1').addEventListener('input', function() {
        document.getElementById('searchForm').submit();
    });

    function toggleSchoolNameField() {
        const studentType = document.getElementById('student_type').value;
        const schoolNameField = document.getElementById('school_name_field');
        if (studentType === 'transferee') {
            schoolNameField.style.display = 'block';
        } else {
            schoolNameField.style.display = 'none';
        }
    }

    // Removed the conflicting Remove Subject button click handler that only removed the subject from the DOM without backend update

    // Drag and Drop handlers for subjects
    let draggedSubjectId = null;

    // Make subjects draggable
    const draggableSubjects = document.querySelectorAll('li.list-group-item[draggable="true"]');
    draggableSubjects.forEach(subject => {
        subject.addEventListener('dragstart', function(e) {
            draggedSubjectId = this.getAttribute('data-subject-id');
            e.dataTransfer.setData('text/plain', draggedSubjectId);
            e.dataTransfer.effectAllowed = 'move';
        });
    });

    // Define drop zone - the card body containing the subjects list
    const dropZones = document.querySelectorAll('.card-body');

    dropZones.forEach(zone => {
        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', function(e) {
            this.classList.remove('drag-over');
        });

        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            const subjectId = e.dataTransfer.getData('text/plain');
            if (!subjectId) return;

            // Get student ID from hidden input or data attribute
            const studentId = document.querySelector('input[name="student_id"]')?.value || window.studentId || null;
            if (!studentId) {
                alert('Student ID not found.');
                return;
            }

            // Send AJAX request to add subject to student
            $.ajax({
                url: '/add_student_subject_ajax/', // Adjust URL if needed
                type: 'POST',
                data: {
                    'student_id': studentId,
                    'new_subject': subjectId,
                },
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                success: function(response) {
                    if (response.success) {
                        alert(response.message);
                        // Optionally update the DOM to add the new subject without reload
                        // For now, reload the page to reflect changes
                        location.reload();
                    } else {
                        alert('Error: ' + response.error);
                    }
                },
                error: function() {
                    alert('An error occurred while adding the subject.');
                }
            });
        });
    });

    // Function to get CSRF token cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // New code: AJAX handler for removing a subject from a student
    document.querySelectorAll('.btn-remove-subject').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const confirmed = confirm('Are you sure you want to remove this subject from the student?');
            if (!confirmed) return;

            const studentId = this.getAttribute('data-student-id');
            const subjectId = this.getAttribute('data-subject-id');
            const listItem = this.closest('li.list-group-item');

            if (!studentId || !subjectId) {
                alert('Student ID or Subject ID not found.');
                return;
            }

            $.ajax({
                url: '/drop_student_subject_ajax/',
                type: 'POST',
                data: {
                    'student_id': studentId,
                    'subject_id': subjectId,
                },
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                success: function(response) {
                    if (response.success) {
                        alert(response.message);
                        // Remove the subject's list item from the DOM
                        if (listItem) {
                            listItem.remove();
                        }
                    } else {
                        alert('Error: ' + response.error);
                    }
                },
                error: function() {
                    alert('An error occurred while removing the subject.');
                }
            });
        });
    });

    // Handle Add Subject form submission
    document.getElementById('addSubjectForm').addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(this);

        fetch("{% url 'add_student_subject_ajax' %}", {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Build new subject list item HTML
                const newSubjectHtml = `
                    <li class="list-group-item d-flex justify-content-between align-items-center" draggable="true" data-subject-id="${data.new_subject_id}">
                        <div>
                            <h5 class="card-title">${data.new_subject_name}</h5>
                            <p class="card-text">
                                <strong>Code:</strong> N/A<br>
                                <strong>Credits:</strong> N/A
                            </p>
                        </div>
                        <div class="btn-group">
                            <button class="btn btn-sm btn-primary me-1 btn-change-subject"
                                    data-student-id="${formData.get('student_id')}"
                                    data-old-subject-id="${data.new_subject_id}"
                                    data-old-subject-name="${data.new_subject_name}">
                                Edit Subject
                            </button>
                            <button class="btn btn-sm btn-danger btn-remove-subject"
                                    data-student-id="${formData.get('student_id')}"
                                    data-subject-id="${data.new_subject_id}"
                                    onclick="return confirm('Are you sure you want to remove this subject from the student?')">
                                Remove Subject
                            </button>
                        </div>
                    </li>
                `;

                // Find the correct <ul> by year-level and semester
                const targetUl = document.querySelector(`ul.list-group[data-year-level="${data.year_level}"][data-semester="${data.semester_offered}"]`);

                if (targetUl) {
                    targetUl.insertAdjacentHTML('beforeend', newSubjectHtml);
                } else {
                    alert('Could not find the correct subject list to add the new subject.');
                }

                // Close the modal after adding
                $('#addSubjectModal').modal('hide');
                // Clear success message after a delay
                setTimeout(() => {
                    document.getElementById('addSubjectSuccess').textContent = '';
                }, 3000);
            } else {
                document.getElementById('addSubjectError').textContent = data.error;
            }
        })
        .catch(() => {
            document.getElementById('addSubjectError').textContent = 'An error occurred while adding the subject.';
        });
    });


