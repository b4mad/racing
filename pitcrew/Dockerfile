FROM quay.io/thoth-station/s2i-thoth-ubi9-py39@sha256:909870d3c1a93f9f9a38b7094209eeeec01c03f659964ecb36b2e90fd424b306

USER 0
ADD . /tmp/src
RUN /usr/bin/fix-permissions /tmp/src
USER 1001

# Thoth Knowledgebase is lacking some packages, lets try using it later
ENV THOTH_OFF=1

RUN /usr/libexec/s2i/assemble

CMD /usr/libexec/s2i/run
