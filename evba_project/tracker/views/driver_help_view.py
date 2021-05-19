import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .measure_dist import distance
from tracker.models import *
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import HttpResponse


@csrf_exempt
def driverSendHelp(request):
    service_id=request.POST['service_id']
    problem_desc = request.POST['problem_desc']
    vehicle_image = request.FILES['vehicle_image']
    radius = float(request.POST['radius'])
    cur_lat = float(request.POST['lat'])
    cur_lon = float(request.POST['lon'])
    # print(radius)
    current_info = {
        'service_id':service_id,
        'problem_desc':problem_desc,
        'cur_lat':cur_lat,
        'cur_lon':cur_lon,
        'vehicle_image':vehicle_image,
        'radius':radius
    }
    
    data = request.session['mechanic_list']['data']
    index = request.session['mechanic_list']['index']
    available_data = return_available_mechanic_list({'lat':cur_lat,'lon':cur_lon},service_id,radius)
    driver = Driver.objects.filter(driverId=request.session['driver_id']).first()

    # print(f"{driver} {available_data}")
    for d in available_data:
        # print(d)
        try:
            data.index(d)
        except :
            data.append(d)


    available_resp = available_running_mechanic(request)

    request.session['mechanic_list']={
    'data':data,
    'index':index
    }
    # print(data)

    if available_resp:
        # print(request.session['running_mechanic_list'])
        resp = available_resp
        # request.session[''] = {
        # 'data':data,
        # 'index':index
        # }
    else:

        mechanic_info = return_not_running_mechanic_info(request)
        # print(mechanic_info)
        if mechanic_info:
            resp = return_response(mechanic_info,request,current_info)
        else:
            resp = {
                'status':False
            }
    print(f"driverSendHelp {request.session['running_mechanic_list']}")
    return JsonResponse(resp)

def return_response(mechanic_info,request,current_info):
   
    mechanic = Mechanic.objects.filter(mechanicId=mechanic_info['mechanic_id']).first()
    mechanic.running = True
    mechanic.save()
    driver = Driver.objects.filter(driverId=request.session['driver_id']).first()
    service = VehicleService.objects.filter(serviceId=current_info['service_id']).first()
    cur_lat = current_info['cur_lat']
    cur_lon = current_info['cur_lon']
    problem_desc = current_info['problem_desc']
    vehicle_image = current_info['vehicle_image']
    help = Help(driver=driver,mechanic=mechanic,service=service,problem_desc=problem_desc,vehicle_image=vehicle_image,cur_lat=cur_lat,cur_lon=cur_lon)
    help.save()
    current_info['help_id'] = help.id
    current_info.pop('vehicle_image')
    request.session['current_driver_info'] =current_info
    send_notifications(mechanic_id=mechanic.mechanicId,distance=mechanic_info['distance'],help=help)
    
    resp = {
            'status':True,
            'data':{
                'id':mechanic.mechanicId,
                'name':f"{mechanic.fname} {mechanic.lname}",
                'lat':mechanic.latitude,
                'lon':mechanic.longitude,
                'distance':mechanic_info['distance'],
                'service':service.name,
                'problem_desc':problem_desc
            }
        }

    return resp

def return_not_running_mechanic_info(request):
    index = request.session['mechanic_list']['index']
    data = request.session['mechanic_list']['data']
    running_mechanic_list = request.session['running_mechanic_list']
    mechanic_info = {}

   
    for i in range(index,len(data)):
        mechanic = Mechanic.objects.filter(mechanicId=data[i]['mechanic_id']).first()
        mechanic_info = data[i]

       
        if mechanic.running:
            index +=1
            try:
                running_mechanic_list.index(data[i])
            except :
                running_mechanic_list.append(data[i])
        else:
            break

    request.session['running_mechanic_list'] = running_mechanic_list
    # print(f"return_not_running_mechanic_info {request.session['running_mechanic_list']}")
    if len(data)>index:
        request.session['mechanic_list'] = {
            'data':data,
            'index':index+1
            }
        return mechanic_info
    else:
        request.session['mechanic_list'] = {
        'data':data,
        'index':index
        }

        return {}


def available_running_mechanic(request):
    
    data = request.session['running_mechanic_list']
    # print(f"available_running_mechanic {data}")
    mechanic_info = {}
    resp = None
    for d in data:
        mechanic = Mechanic.objects.filter(mechanicId=d['mechanic_id']).first()
        if mechanic.running == False:
            current_info = request.session['current_driver_info']
            prev_help = Help.objects.filter(id=current_info['help_id']).first()
            current_info['vehicle_image']=prev_help.vehicle_image
            resp = return_response(mechanic_info=d, request=request, current_info=current_info)
            mechanic_info = d
            break
    
    if mechanic_info:
        data.remove(mechanic_info)
    # print(data)

    request.session['running_mechanic_list'] = data
    # print(request.session['running_mechanic_list'])
    return resp




def send_again_help_request(request):
    # print(request.session['running_mechanic_list'])
    resp = available_running_mechanic(request)
    # print(request.session['running_mechanic_list'])
    
    current_info = request.session['current_driver_info']
    prev_help = Help.objects.filter(id=current_info['help_id']).first()
    # print(resp)
    if resp is None:

        mechanic_info = return_not_running_mechanic_info(request)
        if mechanic_info:
            current_info['vehicle_image']=prev_help.vehicle_image
            resp = return_response(mechanic_info, request, current_info)
        else:
            resp = {
                    'status':False
                }
       
    return JsonResponse(resp)


def return_available_mechanic_list(curr_loc,service_id,radius):
    data = []
    service = VehicleService.objects.filter(serviceId=service_id).first()
    for mechanic in Mechanic.objects.filter(online=True,status="approve"):
        
        loc = {
            'lat':mechanic.latitude,
            'lon':mechanic.longitude
        }
        d = distance(curr_loc,loc)
        if d <=radius:
            t = {
                'mechanic_id':mechanic.mechanicId,
                'distance':d
            }
            data.append(t)
    # print(data)
    data = bubbleSort(data)
    return data


def bubbleSort(data):
    for i in range(len(data)):
        for j in range(i,len(data)-1):
            if data[j]['distance']>data[j+1]['distance']:
                t = data[j]
                data[j]=data[j+1]
                data[j+1] = t
    return data
def send_notifications(mechanic_id,distance,help):
    
    channel_layer = get_channel_layer()
    room_name = f"mechanic_{mechanic_id}"
    # print(room_name)
    mechanic = Mechanic.objects.filter(mechanicId=mechanic_id).first()

    data = {
        'help_id':help.id,
        'driver_id':help.driver.driverId,
        'driver_name':f"{help.driver.fname} {help.driver.lname}",
        'distance':distance,
        'vehicle_image':help.vehicle_image.url,
        'problem_desc':help.problem_desc,
        'service':help.service.name,
        'm_lat':mechanic.latitude,
        'm_lon':mechanic.longitude,
        'd_lat':help.cur_lat,
        'd_lon':help.cur_lon,
    }
    
    async_to_sync(channel_layer.group_send)(
        room_name,
        {
            'type':'send_message',
            'text':data
        }

    )




