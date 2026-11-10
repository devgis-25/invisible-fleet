
from django.urls import path
from api.views import (
    AnalyticsOverviewView,
    AnalyticsTimelineView,
    AnalyticsMapView,
    MaritimeZoneView,
    AnalyticsRankingView,
    AnalyticsTemporalView,
)



urlpatterns = [
    path(
        "analytics/overview/",
        AnalyticsOverviewView.as_view(),
        name="analytics-overview",
    ),
    
    path(
        "analytics/timeline/",
        AnalyticsTimelineView.as_view(),
        name="analytics-timeline",
    ),
    
    path(
        "analytics/map/",
        AnalyticsMapView.as_view(),
        name="analytics-map",
    ),
    
    path(
        "analytics/zone/",
        MaritimeZoneView.as_view(),
        name="analytics-zone"
    ),
        path(
        "analytics/ranking/",
        AnalyticsRankingView.as_view(),
        name="analytics-ranking",
    ),
        path(
    "analytics/temporal/",
    AnalyticsTemporalView.as_view(),
    name="analytics-temporal",
),
]
