import csv
import datetime
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from .models import GlobalsExtrainfo, GlobalsDesignation, GlobalsHoldsdesignation, GlobalsModuleaccess, AuthUser
from .serializers import GlobalExtraInfoSerializer, GlobalsDesignationSerializer, GlobalsModuleaccessSerializer, AuthUserSerializer
from io import StringIO
import random
import string

def create_password(data):
    first_name = data.get('name').split(' ')[0].capitalize()
    roll_no_part = data.get('rollNo')[-3:].upper()
    special_characters = string.punctuation
    random_specials = ''.join(random.choice(special_characters) for _ in range(2))
    return f'{first_name}{roll_no_part}{random_specials}'

# get list of all users
@api_view(['GET'])
def global_extrainfo_list(request):
    records = GlobalsExtrainfo.objects.all()
    serializer = GlobalExtraInfoSerializer(records, many=True)
    return Response(serializer.data)

# get user by email and then fetch the role details 
@api_view(['GET'])
def get_user_role_by_email(request):
    email = request.query_params.get('email')
    
    if not email:
        return Response({"error": "Email parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = AuthUser.objects.get(email=email)
        user_id = user.id
        
        holds_designation_entries = GlobalsHoldsdesignation.objects.filter(user=user_id)
        
        designation_ids = [entry.designation_id for entry in holds_designation_entries]
        
        roles = GlobalsDesignation.objects.filter(id__in=designation_ids)
        roles_serializer = GlobalsDesignationSerializer(roles, many=True)
        
        return Response({
            "user": AuthUserSerializer(user).data,
            "roles": roles_serializer.data,
        }, status=status.HTTP_200_OK)
        
    except AuthUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# update user's roles
@api_view(['PUT'])
def update_user_roles(request):
    email = request.data.get('email')
    roles_to_add = request.data.get('roles')

    if not email or not roles_to_add:
        return Response({"error": "Email and roles are required."}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(AuthUser, email=email)

    # Get existing roles' names as a set of strings
    existing_roles = GlobalsHoldsdesignation.objects.filter(user=user)
    existing_role_names = set(existing_roles.values_list('designation__name', flat=True))

    # Normalize roles_to_add: Extract names from dicts and keep strings
    processed_roles_to_add = set()

    for role in roles_to_add:
        if isinstance(role, dict):
            # Check if 'name' key exists in the dictionary
            if 'name' in role:
                processed_roles_to_add.add(role['name'])  # Extract name from dict
        elif isinstance(role, str):
            processed_roles_to_add.add(role)  # Keep string as is

    print("Processed roles_to_add:", processed_roles_to_add)  # Log processed roles_to_add

    # Find roles to remove
    roles_to_remove = existing_role_names - processed_roles_to_add

    # Remove roles that are not in the new list
    GlobalsHoldsdesignation.objects.filter(user=user, designation__name__in=roles_to_remove).delete()

    # Add new roles
    for role_name in processed_roles_to_add:
        if role_name not in existing_role_names:
            designation = get_object_or_404(GlobalsDesignation, name=role_name)
            GlobalsHoldsdesignation.objects.create(
                held_at=timezone.now(),
                designation=designation,
                user=user,
                working=user
            )

    return Response({"message": "User roles updated successfully."}, status=status.HTTP_200_OK)
        
# get list of all roles
@api_view(['GET'])
def global_designation_list(request):
    records = GlobalsDesignation.objects.all()
    serializer = GlobalsDesignationSerializer(records, many=True)
    return Response(serializer.data) 

# add a new role
@api_view(['POST'])
def add_designation(request):
    serializer = GlobalsDesignationSerializer(data=request.data)
    if serializer.is_valid():
        role = serializer.save()
        data = {
            'designation' : role.name,
            'program_and_curriculum' : False,
            'course_registration' : False,
            'course_management' : False,
            'other_academics' : False,
            'spacs' : False,
            'department' : False,
            'examinations' : False,
            'hr' : False,
            'iwd' : False,
            'complaint_management' : False,
            'fts' : False,
            'purchase_and_store' : False,
            'rspc' : False,
            'hostel_management' : False,
            'mess_management' : False,
            'gymkhana' : False,
            'placement_cell' : False,
            'visitor_hostel' : False,
            'phc' : False,
        }
        module_serializer = GlobalsModuleaccessSerializer(data=data)
        if module_serializer.is_valid():
            module_serializer.save()
        return Response({'role': serializer.data, 'modules': module_serializer.data}, status.HTTP_201_CREATED)
    else :
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    
# delete a role
@api_view(['DELETE'])
def delete_designation(request):
    name = request.data.get('name')
    
    if not name:
        return Response({"error": "No name provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        designation = GlobalsDesignation.objects.get(name=name)
        designation.delete()
        return Response({"message": f"Designation '{name}' deleted successfully."}, status=status.HTTP_200_OK)
    except GlobalsDesignation.DoesNotExist:
        return Response({"error": f"Designation with name '{name}' not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# modify a role
@api_view(['PUT', 'PATCH'])
def update_designation(request):
    name = request.data.get('name')
    
    if not name:
        return Response({"error": "No name provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        designation = GlobalsDesignation.objects.get(name=name)
    except GlobalsDesignation.DoesNotExist:
        return Response({"error": f"Designation with name '{name}' not found."}, status=status.HTTP_404_NOT_FOUND)
    
    partial = request.method == 'PATCH'
    serializer = GlobalsDesignationSerializer(designation, data=request.data, partial=partial)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def add_extra_ino_to_user(request,user):
    extra_info_data = {
        'title': request.data.get('title'),
        'sex': request.data.get('sex'),
        'date_of_birth': request.data.get('date_of_birth'),
        'user_status': request.data.get('user_status'),
        'address': request.data.get('address'),
        'phone_no': request.data.get('phone_no'),
        'user_type': request.data.get('user_type'),
        'profile_picture': request.data.get('profile_picture', None),
        'about_me': request.data.get('about_me'),
        'date_modified': datetime.datetime.now().isoformat(),
        'department': request.data.get('department'),
        'user': user
    }
    extra_info_serializer = GlobalExtraInfoSerializer(data=extra_info_data)
    if extra_info_serializer.is_valid():
        extra_info_serializer.save()
        return Response(extra_info_serializer.data, status=status.HTTP_201_CREATED)
    return Response(extra_info_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def add_user(request):
    data = {
        'password': create_password(request.data),
        'is_superuser': request.data.get('is_superuser') or False,
        'username': request.data.get('rollNo').upper(),
        'first_name': request.data.get('name').split(' ')[0].capitalize(),
        'last_name': ' '.join(request.data.get('name').split(' ')[1:]).capitalize() if len(request.data.get('name').split(' ')) > 1 else '',
        'email': f'{request.data.get('rollNo').upper()}@iiitdmj.ac.in',
        'is_staff': request.data.get('role')=='Student',
        'is_active': True,
        'date_joined': datetime.datetime.now().isoformat(),
    }
    serializer = AuthUserSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def user_detail(request, pk):
    try:
        user = AuthUser.objects.get(pk=pk)
    except AuthUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = AuthUserSerializer(user)
    return Response(serializer.data)

@api_view(['PUT', 'PATCH'])
def update_user(request, pk):
    try:
        user = AuthUser.objects.get(pk=pk)
    except AuthUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    partial = request.method == 'PATCH'
    serializer = AuthUserSerializer(user, data=request.data, partial=partial)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_user(request, pk):
    try:
        user = AuthUser.objects.get(pk=pk)
        user.delete()
        return Response({"message": "User deleted successfully"}, status=status.HTTP_200_OK)
    except AuthUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
def reset_password(request):
    roll_no = request.data.get('rollNo')
    try:
        user = AuthUser.objects.get(username=roll_no.upper())
        new_password = create_password(request.data)
        while new_password == user.password:
            new_password = create_password(request.data)
        
        user.password = new_password
        user.save()
        return Response({"password": new_password,"message": "Password reset successfully."}, status=status.HTTP_200_OK)
    except AuthUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# get module access for a specific role
@api_view(['GET'])
def get_module_access(request):
    role_name = request.query_params.get('designation')
    
    if not role_name:
        return Response({"error": "No role provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        module_access = GlobalsModuleaccess.objects.get(designation=role_name)
    except GlobalsModuleaccess.DoesNotExist:
        return Response({"error": f"Module access for designation '{role_name}' not found."}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = GlobalsModuleaccessSerializer(module_access)
    return Response(serializer.data, status=status.HTTP_200_OK)
    
# modify role access
@api_view(['PUT'])
def modify_moduleaccess(request):
    role_name = request.data.get('designation')
    
    if not role_name:
        return Response({"error": "No role provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        designation = GlobalsModuleaccess.objects.get(designation=role_name)
    except GlobalsModuleaccess.DoesNotExist:
        return Response({"error": f"Designation with name '{designation}' not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = GlobalsModuleaccessSerializer(designation, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#bulk import of users via csv file
@api_view(['POST'])
def bulk_import_users(request):
    if 'file' not in request.FILES:
        return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['file']
    if not file.name.endswith('.csv'):
        return Response({"error": "Please upload a valid CSV file."}, status=status.HTTP_400_BAD_REQUEST)

    file_data = file.read().decode('utf-8')
    csv_data = csv.reader(StringIO(file_data))
    
    headers = next(csv_data)  
    created_users = []
    for row in csv_data:
        try:
            data = {
                'rollNo': row[0],
                'name': row[1],
            }
            user_data = {
                'password': create_password(data),
                'username': row[0].upper(),
                'first_name': row[1].split(' ')[0].capitalize(),
                'last_name': ' '.join(row[1].split(' ')[1:]).capitalize() if len(row[1].split(' ')) > 1 else '',
                'email': f'{row[0].upper()}@iiitdmj.ac.in',
                'is_staff': row[2]=='Student',
                'is_superuser': row[3] or False,
                'is_active': True,
                'date_joined': datetime.datetime.now().isoformat(),
            }
            serializer = AuthUserSerializer(data=user_data)
            if serializer.is_valid():
                serializer.save()
                created_users.append(serializer.data)
            else:
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except IndexError:
            return Response({"error": "Invalid data format."}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": f"{len(created_users)} users created successfully.", "users": created_users}, status=status.HTTP_201_CREATED)

#bulk export of users via csv file
@api_view(['GET'])
def bulk_export_users(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_superuser'])
    users = AuthUser.objects.all()
    
    for user in users:
        writer.writerow([user.username, user.first_name, user.last_name, user.email, user.is_staff, user.is_superuser])
    
    return response