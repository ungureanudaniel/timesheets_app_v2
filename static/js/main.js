$(document).ready(function() {
    // Initialize date picker
    // $('#id_date').datepicker({
    //     format: 'yyyy-mm-dd',
    //     autoclose: true,
    //     todayHighlight: true
    // });
	// // Increment and Decrement Hours
    // $('#increment-hours').click(function(e){
    //     // Stop acting like a button
    //     e.preventDefault();
    //     // Get its current value
    //     var currentVal = parseInt($('#hoursWorked').val());
    //     // If is not undefined
    //     if (!isNaN(currentVal)) {
    //         // Increment
    //         $('#hoursWorked').val(currentVal + 1);
    //     } else {
    //         // Otherwise put a 0 there
    //         $('#hoursWorked').val(0);
    //     }
    // });
    // // This button will decrement the value till 0
    // $(".decrement-hours").click(function(e) {
    //     // Stop acting like a button
    //     e.preventDefault();
    //     // Get its current value
    //     var currentVal = parseInt($('#hoursWorked').val());
    //     // If it isn't undefined or its greater than 0
    //     if (!isNaN(currentVal) && currentVal > 0) {
    //         // Decrement one
    //         $('#hoursWorked').val(currentVal - 1);
    //     } else {
    //         // Otherwise put a 0 there
    //         $('#hoursWorked').val(0);
    //     }
    // });

    // // DUmmy activities
    // myEvents = [
    //       {
    //         id:"required-id-1",
    //         name:"New Year",
    //         date:"Wed Jan 01 2020 00:00:00 GMT-0800 (Pacific Standard Time)",
    //         type:"holiday",
    //         everyYear:true
    //       },
    //       {
    //         id:"required-id-2",
    //         name:"Valentine's Day",
    //         date:"Fri Feb 14 2020 00:00:00 GMT-0800 (Pacific Standard Time)",
    //         type:"holiday",
    //         everyYear:true,
    //         color:"#222"
    //       },
    //       {
    //         id:"required-id-3",
    //         name:"Custom Date",
    //         badge:"08/03 - 08/05",
    //         date: ["August/03/2020","August/05/2020"],
    //         description:"Description here",
    //         type:"event",

    //       },

    //       // more events here
    //     ]
    // // Get calendar events from Django context
    // var calendarEvents = JSON.parse('{{ calendar_events|escapejs }}');
    // // Initialize EvoCalendar with user-specific events
    // $("#evoCalendar").evoCalendar({
    //     theme: 'Midnight Blue',
    //     language: 'ro',
    //     calendarEvents: myEvents,
    //     dates: {
    //           en: {
    //             days: ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],
    //             daysShort: ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],
    //             daysMin: ["Su","Mo","Tu","We","Th","Fr","Sa"],
    //             months: ["January","February","March","April","May","June","July","August","September","October","November","December"],
    //             monthsShort: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    //             noEventForToday:"No event for today.. so take a rest! :)",
    //             noEventForThisDay:"No event for this day.. so take a rest! :)",
    //         },
    //           ro: {
    //             days: ["Duminică","Luni","Marți","Miercuri","Joi","Vineri","Sâmbătă"],
    //             daysShort: ["Dum","Lun","Mar","Mie","Joi","Vin","Sâm"],
    //             daysMin: ["Du","Lu","Ma","Mi","Jo","Vi","Sâ"],
    //             months: ["Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie","Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie"],
    //             monthsShort: ["Ian","Feb","Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Nov","Dec"],
    //             noEventForToday:"Nici o activitate în această zi.. deci ia o pauză! :)",
    //             noEventForThisDay:"Nici o activitate în această zi.. deci ia o pauză! :)",
    //         },}
    //     });
    // // Handle date selection to open modal for adding timesheets
    // $('#evoCalendar').on('selectDate', function(event, newDate) {
    //     // Logic to open a modal to add activities
    //     console.log("Selected date: ", newDate);
    //     $('#timesheetModal').modal('show');
    //     $('#selectedDate').val(newDate);
    // });
});
$(document).ready(function () {
    // Define Romanian locale for Moment.js
    moment.defineLocale('ro', {
        months: 'Ianuarie_Februarie_Martie_Aprilie_Mai_Iunie_Iulie_August_Septebrie_Octombrie_Noiembrie_Decembrie'.split('_'),
        monthsShort: 'Ian_Feb_Mar_Apr_Mai_Iun_Iul_Aug_Sep_Oct_Noi_Dec'.split('_'),
        weekdays: 'Duminică_Luni_Marți_Miercuri_Joi_Vineri_Sâmbătă'.split('_'),
        weekdaysShort: 'Dum_Lun_Mar_Mie_Joi_Vin_Sâm'.split('_'),
        weekdaysMin: 'Du_Lu_Ma_Mi_Jo_Vi_Sâ'.split('_'),
        week: {
            dow: 1, // Monday is the first day of the week.
            doy: 4  // The week that contains Jan 4th is the first week of the year.
        },
        // Add other locale settings as needed
    });
    var calendar = $('#calendar').fullCalendar({
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,agendaWeek,agendaDay'
        },
        locale: 'currentLocale',
        events: '/get_timesheets/',
        selectable: true,
        selectHelper: true,
        editable: true,
        eventLimit: true,
        // When a date is selected, open the modal
        select: function (start, end, allDay) {
            var date = $.fullCalendar.formatDate(start, "YYYY-MM-DD");
            
            // Set the date in the hidden input field in the modal form
            $('#modalDate').val(date);

            // Update modal title (optional)
            $('#timesheetModalLabel').text('Enter Timesheet Data for ' + date);
            
            // Show the modal
            $('#timesheetModal').modal('show');
        },
            error: function() {
                alert('Failed to load the fuckin modal');
        },
        eventResize: function (event) {
            var start = $.fullCalendar.formatDate(event.start, "Y-MM-DD HH:mm:ss");
            var end = $.fullCalendar.formatDate(event.end, "Y-MM-DD HH:mm:ss");
            var title = event.title;
            var id = event.id;
            $.ajax({
                type: "GET",
                url: '/update',
                data: {'title': title, 'start': start, 'end': end, 'id': id},
                dataType: "json",
                success: function (data) {
                    calendar.fullCalendar('refetchEvents');
                    alert('Event Update');
                },
                error: function (data) {
                    alert('There is a problem!!!');
                }
            });
        },

        eventDrop: function (event) {
            var start = $.fullCalendar.formatDate(event.start, "Y-MM-DD HH:mm:ss");
            var end = $.fullCalendar.formatDate(event.end, "Y-MM-DD HH:mm:ss");
            var title = event.title;
            var id = event.id;
            $.ajax({
                type: "GET",
                url: '/update',
                data: {'title': title, 'start': start, 'end': end, 'id': id},
                dataType: "json",
                success: function (data) {
                    calendar.fullCalendar('refetchEvents');
                    alert('Event Update');
                },
                error: function (data) {
                    alert('There is a problem!!!');
                }
            });
        },

        eventClick: function (event) {
            if (confirm("Are you sure you want to remove it?")) {
                var id = event.id;
                $.ajax({
                    type: "GET",
                    url: '/remove',
                    data: {'id': id},
                    dataType: "json",
                    success: function (data) {
                        calendar.fullCalendar('refetchEvents');
                        alert('Event Removed');
                    },
                    error: function (data) {
                        alert('There is a problem!!!');
                    }
                });
            }
        },

    });
});
// $(document).on('submit', '#timesheetForm', function(event) {
//     event.preventDefault();  // Prevent the default form submission

//     var formData = $(this).serialize();  // Get the form data

//     $.ajax({
//         url: $(this).attr('action'),  // This will be '/create_timesheet/'
//         type: 'POST',
//         data: formData,
//         success: function(response) {
//             if (response.status === 'success') {
//                 $('#timesheetModal').modal('hide');  // Hide the modal
//                 alert('Timesheet created successfully!');  // Optionally show a success message
//                 $('#calendar').fullCalendar('refetchEvents');  // Refresh the calendar events
//             } else {
//                 alert(response.message);  // Show error message if any
//             }
//         },
//         error: function() {
//             alert('An error occurred while creating the timesheet.');
//         }
//     });
// });
