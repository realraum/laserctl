import sqlite3 
import curses
import npyscreen
import rfid

#----------------------------------------------------------------------------
#
#  Database access
#
#----------------------------------------------------------------------------
class CardsDB(object):
    def __init__(self, filename="db/cards.db"):
        self.dbfilename = filename
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute(
          "CREATE TABLE IF NOT EXISTS cards(\
           id integer primary key,\
           uid CHAR(128),\
           vorname TEXT not null,\
           nachname TEXT not null,\
           units int,\
           active int\
           )")
        db.commit()
        c.close()

    def add_card(self, vorname = '', nachname='', units=0):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('INSERT INTO cards(vorname, nachname, units, active) \
                    VALUES(?,?,?,?)', (vorname, nachname, units, 1))
        db.commit()
        c.close()

    def update_card(self, id, vorname = '', nachname='', units=0, active = 1):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('UPDATE cards set vorname=?, nachname=?, units=?, active=? \
                    WHERE id=?', (vorname, nachname, units, active, id))
        db.commit()
        c.close()

    def delete_card(self, id):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('DELETE FROM cards where id=?', (id,))
        db.commit()
        c.close()

    def list_all_cards(self, ):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT id, vorname, nachname, units, active from cards')
        records = c.fetchall()
        c.close()
        return records

    def get_card(self, id):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT id, vorname, nachname, units, active  from cards WHERE id=?', (id,))
        records = c.fetchall()
        c.close()
        return records[0]

    def cardExists(self, uid):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT id from cards WHERE uid=?', (uid,))
        records = c.fetchone()
        c.close()
        if records == None:
            return -1
        else: 
            return records[0]

    def update_units(self, id, units):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('UPDATE cards set units=units+?\
                    WHERE id=?', (units, id))
        db.commit()
        c.close()