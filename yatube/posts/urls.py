from django.urls import path

from . import views

app_name = 'posts'

handler404 = 'core.views.page_not_found'


urlpatterns = [
    path('', views.index, name='home'),
    path('create/', views.post_create, name='post_create'),
    path('follow/', views.follow_index, name='follow_index'),
    path('group/<slug:slug>/', views.goup_posts, name='group_posts'),
    path('profile/<str:username>/follow/',
         views.profile_follow, name='profile_follow'
         ),
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    path('posts/<int:post_id>/comment/',
         views.add_comment, name='add_comment'
         ),
    path('posts/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path(
        'profile/<str:username>/unfollow/',
        views.profile_unfollow, name='profile_unfollow'
    ),
]
