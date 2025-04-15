 $(document).ready(function() {
        const body = $('body');
        const sidebar = $('.main-sidebar');
        const backdrop = $('body::after');

        $('[data-widget="pushmenu"]').on('click', function(e) {
            e.preventDefault();

            if ($(window).width() <= 768) {
                sidebar.toggleClass('sidebar-open');
                body.toggleClass('sidebar-open-mobile');
            } else {
                body.toggleClass('sidebar-collapse');
            }
        });

        $(document).on('click', function(e) {
            if (body.hasClass('sidebar-open-mobile') && $(e.target).is(body)) {
                if (!$(e.target).closest('.main-sidebar').length && !$(e.target).closest('[data-widget="pushmenu"]').length) {
                    sidebar.removeClass('sidebar-open');
                    body.removeClass('sidebar-open-mobile');
                }
            }
        });

        $('.dropdown > a[data-toggle="dropdown"]').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const $dropdown = $(this).parent('.dropdown');
            const wasActive = $dropdown.hasClass('active');

            $('.dropdown').removeClass('active');

            if (!wasActive) {
                $dropdown.addClass('active');
            }
        });

        $(document).on('click', function(e) {
            if (!$(e.target).closest('.dropdown').length) {
                $('.dropdown').removeClass('active');
            }
        });

        $('.nav-sidebar .has-treeview > a').on('click', function(e) {
            e.preventDefault();
            const $parentLi = $(this).parent('li.has-treeview');

            if ($parentLi.closest('[data-accordion="false"]').length === 0) {
                $parentLi.siblings('.has-treeview.menu-open').removeClass('menu-open').find('.nav-treeview').slideUp();
            }

            $parentLi.toggleClass('menu-open');
            $parentLi.find('> .nav-treeview').slideToggle();
        });

        $('.content-wrapper').on('scroll', function() {
            const $header = $('.main-header');
            if ($(this).scrollTop() > 10) {
                $header.css('box-shadow', 'var(--box-shadow-md)');
            } else {
                $header.css('box-shadow', 'var(--box-shadow)');
            }
        });
    });

