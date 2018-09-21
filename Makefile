DESTDIR=
PREFIX=/usr
NAME=ec2imgutils
MANPATH=/usr/share/man
dirs = lib man
files = Makefile README.md LICENSE ec2deprecateimg ec2publishimg setup.py

verSpec = $(shell rpm -q --specfile --qf '%{VERSION}' *.spec)
verSrc = $(shell cat lib/ec2utils/VERSION)

ifneq "$(verSpec)" "$(verSrc)"
$(error "Version mismatch, will not take any action")
endif

clean:
	@find . -name "*.pyc" | xargs rm -f 
	@find . -name "__pycache__" | xargs rm -rf
	@find . -name "*.cache" | xargs rm -rf
	@find . -name "*.egg-info" | xargs rm -rf

pep8: clean
	@pep8 -v --statistics lib/ec2utils/*
	@pep8 -v --statistics --ignore=E402 tests/*.py

tar: clean
	rm -rf $(NAME)-$(verSrc)
	mkdir $(NAME)-$(verSrc)
	mkdir -p "$(NAME)-$(verSrc)"/man/man1
	cp -r $(dirs) $(files) "$(NAME)-$(verSrc)"
	tar -cjf "$(NAME)-$(verSrc).tar.bz2" "$(NAME)-$(verSrc)"
	rm -rf "$(NAME)-$(verSrc)"

test:
	py.test tests/ec2utilsutilstest.py

install:
	python3 setup.py install --prefix="$(PREFIX)" --root="$(DESTDIR)"
	install -d -m 755 "$(DESTDIR)"/"$(MANDIR)"/man1
	install -m 644 man/man1/* "$(DESTDIR)"/"$(MANDIR)"/man1
	gzip "$(DESTDIR)"/"$(MANDIR)"/man1/ec2deprecateimg.1
	gzip "$(DESTDIR)"/"$(MANDIR)"/man1/ec2publishimg.1
