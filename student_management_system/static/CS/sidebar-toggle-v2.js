document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');

    function handleToggle() {
        if (window.innerWidth <= 1024) {
            sidebar.classList.toggle('show');
            sidebar.classList.remove('collapsed');
        } else {
            sidebar.classList.toggle('collapsed');
            sidebar.classList.remove('show');
        }
    }

    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener('click', handleToggle);

        window.addEventListener('resize', function() {
            if (window.innerWidth <= 1024) {
                sidebar.classList.remove('collapsed');
            } else {
                sidebar.classList.remove('show');
            }
        });
    }
});

document.addEventListener('DOMContentLoaded', function () {
    var carouselElement = document.getElementById('collegeCarousel');
    var carousel = bootstrap.Carousel.getInstance(carouselElement);
    if (!carousel) {
        carousel = new bootstrap.Carousel(carouselElement);
    }

    var items = carouselElement.querySelectorAll('.carousel-item');
    items.forEach(function (item) {
        item.addEventListener('click', function (event) {
            var rect = item.getBoundingClientRect();
            var clickX = event.clientX - rect.left;
            if (clickX < rect.width / 2) {
                carousel.prev();
            } else {
                carousel.next();
            }
        });
    });
});


let startX = 0;
let endX = 0;
let isDragging = false;

function handleSwipe() {
    const threshold = 40; // Minimum px to consider swipe
    if (endX < startX - threshold) {
        console.log('Swipe left detected');
        const nextButton = carousel.querySelector('.carousel-control-next');
        if (nextButton) nextButton.click();
    } else if (endX > startX + threshold) {
        console.log('Swipe right detected');
        const prevButton = carousel.querySelector('.carousel-control-prev');
        if (prevButton) prevButton.click();
    }
}

// Touch events
carousel.addEventListener('touchstart', function(e) {
    startX = e.touches[0].clientX;
}, false);

carousel.addEventListener('touchend', function(e) {
    endX = e.changedTouches[0].clientX;
    handleSwipe();
}, false);

// Mouse events for desktop swipe-like behavior
carousel.addEventListener('mousedown', function(e) {
    isDragging = true;
    startX = e.clientX;
}, false);

carousel.addEventListener('mouseup', function(e) {
    if (!isDragging) return;
    isDragging = false;
    endX = e.clientX;
    handleSwipe();
}, false);

carousel.addEventListener('mouseleave', function(e) {
    if (isDragging) {
        isDragging = false;
        endX = e.clientX;
        handleSwipe();
    }
}, false);

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

// Scroll to top button functionality
        var scrollToTopBtn = document.getElementById('scrollToTopBtn');

        window.addEventListener('scroll', function () {
            if (window.scrollY > 300) {
                scrollToTopBtn.style.display = 'flex';
            } else {
                scrollToTopBtn.style.display = 'none';
            }
        });

        scrollToTopBtn.addEventListener('click', function () {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });