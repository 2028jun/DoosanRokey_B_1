from setuptools import find_packages, setup

package_name = 'auto_make_hamburger'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='junhyeok',
    maintainer_email='junhyeok@todo.todo',
    description='TODO: Package description',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'dummy_robot_node = auto_make_hamburger.dummy_robot_node:main',
            'cooking_manager_node = auto_make_hamburger.cooking_manager_node:main',
            'ui_node = auto_make_hamburger.ui_node:main',
        ],
    },
)
