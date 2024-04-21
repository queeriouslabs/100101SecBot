import asyncio
from copy import deepcopy
from datetime import datetime
from comms import create_comms
from database import read_acl_data


class Authorizer:

    def __init__(self):
        self.name = "authorizer"
        self.comms = create_comms(self.name)
        self.hours = None
        self.rfids = None
        self.authorities = ['/open']
        self.load_acl_data()

    def load_acl_data(self):
        """ Load or reload the access control data """
        new_data = read_acl_data()
        self.hours = new_data['hours']
        self.rfids = new_data['rfids']

    def command_handler(self, request):
        commands = request.pop('permissions')
        for cmd in commands:
            if cmd.get('perm') == '/reload':
                self.load_acl_data()
                self.comms.logger.warning("Reloading ACL data")

    def lookup(self, permission, ctx):
        """ Looks up the requested permission using data in the provided
        context.  Returns True if there's a match, false otherwise.
        """
        if "identity" not in ctx:
            raise ValueError("Request Missing Identity")

        # Check that the requested ID is in the known RFIDs
        identity = ctx.pop('identity')
        self.comms.logger.info(f"attempt for: {identity}")
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
            # create and send out response
            response = deepcopy(request)
            response['code'] = 0
            response['msg'] = "OK"
            response.pop('permissions')
            await self.comms.out_q.put(response)

            target_id = request['target_id']
            self.comms.logger.info(f"Got request for {target_id}")
            # Targetting me, handle it and continue
            if target_id == self.name:
                self.command_handler(request)
                continue

            grant = deepcopy(request)

            if target_id == 'front_door_latch':
                self.grant_permissions(grant)

            self.comms.logger.info(f"sent request: {grant}")
            await self.comms.request(target_id, grant)


if __name__ == "__main__":
    auth = Authorizer()
    loop = asyncio.get_event_loop()
    loop.create_task(auth.process())
    loop.run_forever()
