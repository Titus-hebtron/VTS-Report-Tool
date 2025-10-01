from db_utils import add_user

# Add users for different contractors
# Wizpro (id=1), Paschal (id=2), RE Office (id=3), Avators (id=4)

# Admin users
add_user('admin', 'Pass@12345', 'Administrator', contractor_id=3, role='re_admin')
add_user('wizpro_admin', 'Pass@12345', 'Wizpro Admin', contractor_id=1, role='admin')
add_user('paschal_admin', 'Pass@12345', 'Paschal Admin', contractor_id=2, role='admin')

# Regular users
add_user('wizpro_user', 'Pass@12345', 'Wizpro User', contractor_id=1, role='contractor')
add_user('paschal_user', 'Pass@12345', 'Paschal User', contractor_id=2, role='contractor')
add_user('avators_user', 'Pass@12345', 'Avators User', contractor_id=4, role='contractor')

print("All users added successfully.")

