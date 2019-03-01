import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { FeedbackHistoryViewComponent } from './feedback-history-view.component';

describe('FeedbackHistoryViewComponent', () => {
  let component: FeedbackHistoryViewComponent;
  let fixture: ComponentFixture<FeedbackHistoryViewComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ FeedbackHistoryViewComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(FeedbackHistoryViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
