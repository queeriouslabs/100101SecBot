import asyncio
import csv
from copy import deepcopy
from datetime import datetime
from comms import create_comms


def read_data():
    """ reads persistent data from the filesystem
    """
    hours = {}
    rfids = {}

    with open("data/hours.csv", 'r') as f:
        hours_csv = csv.reader(f)
        next(hours_csv)  # drop header
        for row in hours_csv:
            hours[row.pop(0)] = row

    with open("data/rfids.csv", 'r') as f:
        rfids_csv = csv.DictReader(f)
        for row in rfids_csv:
            rfids[row.pop('rfid')] = row

    return {'hours': hours, 'rfids': rfids}


class Authorizer:

    def __init__(self):
        self.comms = create_comms("authorizer")
        self.hours = None
        self.rfids = None
        self.authorities = ['/open']
        self.load_acl_data()

    def load_acl_data(self):
        """ Load or reload the access control data """
        new_data = read_data()
        self.hours = new_data['hours']
        self.rfids = new_data['rfids']

    def lookup(self, permission, ctx):
        """ Looks up the requested permission using data in the provided
        context.  Returns True if there's a match, false otherwise.
        """
        if "identity" not in ctx:
            raise ValueError("Request Missing Identity")

        # Check that the requested ID is in the known RFIDs
        identity = ctx.pop('identity')
        if identity not in self.rfids:
            return False

        # If RFID is known, check access rules
        rules = self.rfids[identity]
        allowed_hours = self.hours[rules['access_times']]
        start_time, end_time = map(int, allowed_hours)
        this_hour = datetime.now().hour  # local time, not UTC
        # this_hour is before the endtime since end_time is the label of the
        # hour a user should not have access.
        if ((start_time <= this_hour) and (this_hour < end_time)):
            return True

        # attempted access outside allowed rules
        return False

    def grant_permissions(self, request):

        for i, perm_req in enumerate(request['permissions']):
            grant = False
            perm = perm_req['perm']
            ctx = perm_req['ctx']
            if perm in self.authorities:
                try:
                    grant = self.lookup(perm, ctx)
                except Exception as e:
                    grant = False
                    ctx = {"error": f"{e}"}
                    self.comms.logger.error(f"{e}")
            request['permissions'][i]['grant'] = grant

    async def process(self):

        self.comms.start()

        while True:
            request = await self.comms.in_q.get()

            grant = deepcopy(request)
            # create and send out response
            response = deepcopy(request)
            response['code'] = 0
            response['msg'] = "OK"
            response.pop('permissions')
            await self.comms.out_q.put(response)

            target_id = grant['target_id']
            self.comms.logger.info(f"Got request for {target_id}")
            if target_id == 'front_door_latch':
                self.grant_permissions(grant)

            self.comms.logger.info(f"sent request: {grant}")
            await self.comms.request(target_id, grant)


if __name__ == "__main__":
    auth = Authorizer()
    loop = asyncio.get_event_loop()
    loop.create_task(auth.process())
    loop.run_forever()
