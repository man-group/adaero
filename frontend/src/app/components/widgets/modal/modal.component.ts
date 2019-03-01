import { Component, Input, Output } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-modal',
  templateUrl: './modal.component.html',
  styleUrls: ['./modal.component.scss']
})
export class ModalComponent {

  @Input() public confirmText: string;
  @Input() public cancelText: string;
  @Input() public dialog: string;
  @Input() public metadata: string;
  constructor(public activeModal: NgbActiveModal) { }

}
