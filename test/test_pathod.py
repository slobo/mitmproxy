from libpathod import pathod, version
from netlib import tcp, http
import tutils

class TestPathod:
    def test_instantiation(self):
        p = pathod.Pathod(
                ("127.0.0.1", 0),
                anchors = [(".*", "200")]
            )
        assert p.anchors
        tutils.raises("invalid regex", pathod.Pathod, ("127.0.0.1", 0), anchors=[("*", "200")])
        tutils.raises("invalid page spec", pathod.Pathod, ("127.0.0.1", 0), anchors=[("foo", "bar")])

    def test_logging(self):
        p = pathod.Pathod(("127.0.0.1", 0))
        assert len(p.get_log()) == 0
        id = p.add_log(dict(s="foo"))
        assert p.log_by_id(id)
        assert len(p.get_log()) == 1
        p.clear_log()
        assert len(p.get_log()) == 0

        for i in range(p.LOGBUF + 1):
            p.add_log(dict(s="foo"))
        assert len(p.get_log()) <= p.LOGBUF


class CommonTests(tutils.DaemonTests):
    def test_sizelimit(self):
        r = self.get("200:b@1g")
        assert r.status_code == 800
        l = self.d.log()[0]
        assert "too large" in l["response"]["error"]

    def test_preline(self):
        v = self.pathoc(r"get:'/p/200':i0,'\r\n'")
        assert v[1] == 200

    def test_info(self):
        assert tuple(self.d.info()["version"]) == version.IVERSION

    def test_logs(self):
        l = len(self.d.log())
        rsp = self.get("202")
        assert len(self.d.log()) == l+1
        assert self.d.clear_log()
        assert len(self.d.log()) == 0

    def test_disconnect(self):
        rsp = self.get("202:b@100k:d200")
        assert len(rsp.content) < 200

    def test_parserr(self):
        rsp = self.get("400:msg,b:")
        assert rsp.status_code == 800

    def test_static(self):
        rsp = self.get("200:b<file")
        assert rsp.status_code == 200
        assert rsp.content.strip() == "testfile"

    def test_anchor(self):
        rsp = self.getpath("anchor/foo")
        assert rsp.status_code == 202

    def test_invalid_first_line(self):
        c = tcp.TCPClient("localhost", self.d.port)
        c.connect()
        if self.SSL:
            c.convert_to_ssl()
        c.wfile.write("foo\n\n\n")
        c.wfile.flush()
        l = self.d.log()[0]
        assert l["type"] == "error"
        assert "foo" in l["msg"]

    def test_invalid_body(self):
        tutils.raises(http.HttpError, self.pathoc, "get:/:h'content-length'='foo'")
        l = self.d.log()[0]
        assert l["type"] == "error"
        assert "Invalid" in l["msg"]

    def test_access_denied(self):
        rsp = self.get("=nonexistent")
        assert rsp.status_code == 800

    def test_source_access_denied(self):
        rsp = self.get("200:b</foo")
        assert rsp.status_code == 800
        assert "Access Denied" in rsp.content


class TestDaemon(CommonTests):
    SSL = False


class TestDaemonSSL(CommonTests):
    SSL = True
    def test_ssl_conn_failure(self):
        c = tcp.TCPClient("localhost", self.d.port)
        c.rbufsize = 0
        c.wbufsize = 0
        c.connect()
        try:
            while 1:
                c.wfile.write("\r\n\r\n\r\n")
        except:
            pass
        l = self.d.log()[0]
        assert l["type"] == "error"
        assert "SSL" in l["msg"]


