DESTDIR=
PREFIX=/usr
NAME=ec2utilsbase
dirs = lib
files = Makefile README.md LICENSE setup.py

nv = $(shell rpm -q --specfile --qf '%{NAME}-%{VERSION}\n' *.spec)
verSpec = $(shell rpm -q --specfile --qf '%{VERSION}' *.spec)
verSrc = $(shell cat lib/ec2utils/base_VERSION)
ifneq "$(verSpec)" "$(verSrc)"
$(error "Version mismatch, will not take any action")
endif

tar:
	rm -rf $(NAME)-$(verSrc)
	mkdir $(NAME)-$(verSrc)
	cp -r $(dirs) $(files) "$(NAME)-$(verSrc)"
	tar -cjf "$(NAME)-$(verSrc).tar.bz2" "$(NAME)-$(verSrc)"
	rm -rf "$(NAME)-$(verSrc)"

test:
	find . -name "*.py" | xargs pep8
	nosetests tests/ec2utilsutilstest.py

install:
	python setup.py install --prefix="$(PREFIX)" --root="$(DESTDIR)"
