import models
import unittest

class TestSimpleModel(unittest.TestCase):

    def test_creation(self):
        s = models.Service(slug="service-foo", name="Service Foo", 
                           description="A wonderful service")
        s.put()
        fetched_s = models.Service.all().filter('slug =', "service-foo").get()
        self.assertEquals(fetched_s.name, "Service Foo")
