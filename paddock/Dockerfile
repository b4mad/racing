FROM quay.io/thoth-station/s2i-thoth-f35-py310@sha256:f2fbf1e0ff31c6f8b1f8ceaccb8b2ada80681d5f9f3f4a157af5dd81ae98b5f5

USER 0
ADD . /tmp/src
RUN /usr/bin/fix-permissions /tmp/src
USER 1001

# Thoth Knowledgebase is lacking some packages, lets try using it later
ENV THOTH_OFF=1

RUN /usr/libexec/s2i/assemble

# https://muafzal.medium.com/creating-django-web-app-in-red-hat-openshift-bae007bfaaff
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
