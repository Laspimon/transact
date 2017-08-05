import unittest

import server

class TestIndex(unittest.TestCase):

    def test_index_returns_greeting(self):
        self.assertEquals(server.index(), 'Hello World')

if __name__ == '__main__':
    unittest.main()
